from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils import timezone
from datetime import timedelta, datetime

from valhalla.proposals.models import TimeAllocation
from valhalla.userrequests.models import Request, Target, Window, UserRequest, Location, Molecule, Constraints
from valhalla.userrequests.state_changes import debit_ipp_time, TimeAllocationError, validate_ipp
from valhalla.common.configdb import ConfigDB
from valhalla.userrequests.duration_utils import (get_request_duration, get_total_duration_dict,
                                                  get_time_allocation_key)
from valhalla.common.rise_set_utils import get_rise_set_intervals


class ConstraintsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Constraints
        exclude = ('request', 'id')


class MoleculeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Molecule
        exclude = ('request', 'id', 'sub_x1', 'sub_x2', 'sub_y1', 'sub_y2')

    def validate_instrument_name(self, value):
        configdb = ConfigDB()
        if value and value not in configdb.get_active_instrument_types({}):
            raise serializers.ValidationError(
                _("Invalid instrument name {}. Valid instruments may include: {}").format(
                    value, ', '.join(configdb.get_active_instrument_types({}))
                )
            )
        return value

    def validate(self, data):
        # set special defaults if it is a spectrograph
        configdb = ConfigDB()
        if configdb.is_spectrograph(data['instrument_name']):
            if 'ag_mode' not in data:
                data['ag_mode'] = 'ON'
            if 'spectra_slit' not in data:
                data['spectra_slit'] = 'floyds_slit_default'

        types_that_require_filter = ['expose', 'auto_focus', 'zero_pointing', 'standard', 'sky_flat']

        # check that the filter is available in the instrument type specified
        available_filters = configdb.get_filters(data['instrument_name'])
        if configdb.is_spectrograph(data['instrument_name']):
            if data['spectra_slit'] not in available_filters:
                raise serializers.ValidationError(
                    _("Invalid spectra slit {} for instrument {}. Valid slits are: {}").format(
                        data['spectra_slit'], data['instrument_name'], ", ".join(available_filters)
                    )
                )
        elif data['type'].lower() in types_that_require_filter:
            if 'filter' not in data:
                raise serializers.ValidationError(
                    _("Molecule type {} with instrument {} must specify a filter.").format(
                        data['type'], data['instrument_name']
                    )
                )
            elif data['filter'] not in available_filters:
                raise serializers.ValidationError(
                    _("Invalid filter {} for instrument {}. Valid filters are: {}").format(
                        data['filter'], data['instrument_name'], ", ".join(available_filters)
                    )
                )

        # check that the binning is available for the instrument type specified
        if 'bin_x' not in data and 'bin_y' not in data:
            data['bin_x'] = configdb.get_default_binning(data['instrument_name'])
            data['bin_y'] = data['bin_x']
        elif 'bin_x' in data and 'bin_y' in data:
            available_binnings = configdb.get_binnings(data['instrument_name'])
            if data['bin_x'] not in available_binnings:
                msg = _("Invalid binning of {} for instrument {}. Valid binnings are: {}").format(
                    data['bin_x'], data['instrument_name'].upper(), ", ".join([str(b) for b in available_binnings])
                )
                raise serializers.ValidationError(msg)
        else:
            raise serializers.ValidationError(_("Missing one of bin_x or bin_y. Specify both or neither."))

        return data


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        exclude = ('request', 'id')

    def validate(self, data):
        if 'observatory' in data and 'site' not in data:
            raise serializers.ValidationError(_("Must specify a site with an observatory."))
        if 'telescope' in data and 'observatory' not in data:
            raise serializers.ValidationError(_("Must specify an observatory with a telescope."))

        configdb = ConfigDB()
        site_json = configdb.get_site_data()
        site_data_dict = {site['code']: site for site in site_json}
        if 'site' in data:
            if data['site'] not in site_data_dict:
                msg = _('Site {} not valid. Valid choices: {}').format(data['site'], ', '.join(site_data_dict.keys()))
                raise serializers.ValidationError(msg)
            obs_set = site_data_dict[data['site']]['enclosure_set']
            obs_dict = {obs['code']: obs for obs in obs_set}
            if 'observatory' in data:
                if data['observatory'] not in obs_dict:
                    msg = _('Observatory {} not valid. Valid choices: {}').format(
                        data['observatory'],
                        ', '.join(obs_dict.keys())
                    )
                    raise serializers.ValidationError(msg)

                tel_set = obs_dict[data['observatory']]['telescope_set']
                tel_list = [tel['code'] for tel in tel_set]
                if 'telescope' in data and data['telescope'] not in tel_list:
                    msg = _('Telescope {} not valid. Valid choices: {}').format(data['telescope'], ', '.join(tel_list))
                    raise serializers.ValidationError(msg)

        return data


class WindowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Window
        exclude = ('request', 'id')

    def validate(self, data):
        if data['end'] <= data['start']:
            msg = _("Window end '{}' cannot be earlier than window start '{}'.").format(data['start'], data['end'])
            raise serializers.ValidationError(msg)
        return data

    def validate_end(self, value):
        # if end time is earlier than current time, through windows in future error
        if value < timezone.now():
            error_dict = {'end': [_('Window end time must be in the future')]}
            raise serializers.ValidationError(error_dict)
        return value


class TargetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Target
        exclude = ('request', 'id')

    def _cleanup_fields(self, data):
        allowed = ('name', 'type')
        if data['type'] == 'SIDEREAL' or data['type'] == 'STATIC':
            allowed += (
                'ra', 'dec', 'proper_motion_ra', 'proper_motion_dec', 'parallax',
                'coordinate_system', 'equinox', 'epoch', 'acquire_mode', 'rot_mode', 'rot_angle'
            )
        elif data['type'] == 'NON_SIDEREAL':
            allowed += ('epochofel', 'orbinc', 'longascnode', 'eccentricity', 'scheme')
            if data['scheme'] == 'ASA_MAJOR_PLANET':
                allowed += ('longofperih', 'meandist', 'meanlong', 'dailymot')
            elif data['scheme'] == 'ASA_MINOR_PLANET':
                allowed += ('argofperih', 'meandist', 'meananom')
            elif data['scheme'] == 'ASA_COMET':
                allowed += ('argofperih', 'perihdist', 'epochofperih')
            elif data['scheme'] == 'JPL_MAJOR_PLANET':
                allowed += ('argofperih', 'meandist', 'meananom', 'dailymot')
            elif data['scheme'] == 'JPL_MINOR_PLANET':
                allowed += ('argofperih', 'perihdist', 'epochofperih')
            elif data['scheme'] == 'MPC_MINOR_PLANET':
                allowed += ('argofperih', 'meandist', 'meananom')
            elif data['scheme'] == 'MPC_COMET':
                allowed += ('argofperih', 'perihdist', 'epochofperih')
        elif data['type'] == 'SATELLITE':
            allowed += (
                'altitude', 'azimuth', 'diff_pitch_rate', 'diff_roll_rate', 'diff_epoch_rate',
                'diff_pitch_acceleration', 'diff_roll_acceleration'
            )

        # Drop any fields that are not specified in the `fields` argument.
        existing = set(self.fields.keys())
        for field_name in existing - set(allowed):
            self.fields.pop(field_name)

    def validate(self, data):
        self._cleanup_fields(data)
        if data['type'] == 'SIDEREAL' or data['type'] == 'STATIC':
            data = self._validate_sidereal_target(data)
        elif data['type'] == 'NON_SIDEREAL':
            data = self._validate_nonsidereal_target(data)
        elif data['type'] == 'SATELLITE':
            data = self._validate_satellite_target(data)
        else:
            raise serializers.ValidationError(_('Invalid target type {}'.format(data['type'])))
        return data

    def _validate_sidereal_target(self, data):
        # check that sidereal specific defaults are filled in
        data.setdefault('coordinate_system', default='ICRS')
        data.setdefault('equinox', default='J2000')

        # Complain if proper motion has been provided, and there is no explicit epoch
        if ('proper_motion_ra' in data or 'proper_motion_dec' in data) and 'epoch' not in data:
            raise serializers.ValidationError(_('Epoch is required when proper motion is specified.'))
        # Otherwise, set epoch to 2000
        elif 'epoch' not in data:
            data['epoch'] = 2000.0

        data.setdefault('proper_motion_ra', 0.0)
        data.setdefault('proper_motion_dec', 0.0)
        data.setdefault('parallax', 0.0)

        # now check that if 'ra' exists 'dec' also exists
        self._validate_require_allowed_fields(data, ['ra','dec'])
        return data

    def _validate_nonsidereal_target(self, data):
        self._validate_require_allowed_fields(data)

        # Tim wanted an eccentricity limit of 0.9 for non-comet targets
        eccentricity_limit = 0.9
        scheme = data['scheme']
        if 'COMET' not in scheme.upper() and data['eccentricity'] > eccentricity_limit:
            msg = _("Non sidereal pointing of scheme {} requires eccentricity to be lower than {}. ").format(
                scheme, eccentricity_limit
            )
            msg += _("Submit with scheme MPC_COMET to use your eccentricity of {}.").format(data['eccentricity'])
            raise serializers.ValidationError(msg)

        return data

    def _validate_satellite_target(self, data):
        self._validate_require_allowed_fields(data)
        return data

    def _validate_require_allowed_fields(self, data, required_fields=None):
        error_dict = {}
        if not required_fields:
            required_fields = self.fields
        for field in required_fields:
            if field not in data:
                error_dict[field] = ['Missing required field']

        if error_dict:
            raise serializers.ValidationError(error_dict)


class RequestSerializer(serializers.ModelSerializer):
    location = LocationSerializer()
    constraints = ConstraintsSerializer()
    target = TargetSerializer()
    molecules = MoleculeSerializer(many=True, source='molecule_set')
    windows = WindowSerializer(many=True, source='window_set')

    class Meta:
        model = Request
        read_only_fields = (
            'id', 'fail_count', 'scheduled_count', 'created', 'completed'
        )
        exclude = ('user_request',)

    def validate_molecules(self, value):
        if not value:
            raise serializers.ValidationError(_('You must specify at least 1 molecule'))
        return value

    def validate(self, data):
        # Target special validation
        if data['molecule_set'][0]['instrument_name'].upper() == '2M0-FLOYDS-SCICAM':
            if 'acquire_mode' not in data['target']:
                # the normal default is 'OPTIONAL', but for floyds the default is 'ON'
                data['target']['acquire_mode'] = 'ON'

        configdb = ConfigDB()

        # check if the instrument specified is allowed
        valid_instruments = configdb.get_active_instrument_types(data['location'])
        for molecule in data['molecule_set']:
            if molecule['instrument_name'] not in valid_instruments:
                msg = _("Invalid instrument name '{}' at site={}, obs={}, tel={}. \n").format(
                    molecule['instrument_name'], data['location'].get('site', 'Any'),
                    data['location'].get('observatory', 'Any'), data['location'].get('telescope', 'Any'))
                msg += _("Valid instruments include: ")
                for inst_name in valid_instruments:
                    msg += inst_name + ', '
                raise serializers.ValidationError(msg)

        instrument_type = data['molecule_set'][0]['instrument_name'].upper()

         # check that the requests window has enough rise_set visible time to accomodate the requests duration
        duration = get_request_duration(instrument_type,
                                        data['molecule_set'], data['target'].get('acquire_mode'))
        rise_set_intervals = get_rise_set_intervals(instrument_type,
                                                    data['target'],
                                                    data['constraints'],
                                                    data['location'],
                                                    data['window_set'])
        largest_interval = timedelta(seconds=0)
        for interval in rise_set_intervals:
            largest_interval = max((interval[1]-interval[0]), largest_interval)
        if largest_interval.total_seconds() <= duration:
            raise serializers.ValidationError(
                _("The request duration {} did not fit into any visible intervals. "
                  "The largest visible interval within your window was {}").format(
                        duration / 3600.0, largest_interval.total_seconds() / 3600.0))

        return data


class UserRequestSerializer(serializers.ModelSerializer):
    requests = RequestSerializer(many=True, source='request_set', required=True)
    submitter = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = UserRequest
        fields = '__all__'
        read_only_fields = (
            'id', 'submitter', 'created', 'state', 'modified'
        )

    @transaction.atomic
    def create(self, validated_data):
        request_data = validated_data.pop('request_set')

        user_request = UserRequest.objects.create(**validated_data)

        for r in request_data:
            target_data = r.pop('target')
            constraints_data = r.pop('constraints')
            window_data = r.pop('window_set')
            molecule_data = r.pop('molecule_set')
            location_data = r.pop('location')

            request = Request.objects.create(user_request=user_request, **r)
            Location.objects.create(request=request, **location_data)
            Target.objects.create(request=request, **target_data)
            Constraints.objects.create(request=request, **constraints_data)

            for data in window_data:
                Window.objects.create(request=request, **data)
            for data in molecule_data:
                Molecule.objects.create(request=request, **data)

        debit_ipp_time(user_request)

        return user_request

    def validate(self, data):
        # check that the user belongs to the supplied proposal
        user = User.objects.get(username=data['submitter'])
        if not user.proposal_set.filter(id=data['proposal']):
            raise serializers.ValidationError(
                _('You do not belong to the proposal you are trying to submit')
            )

        # validation on the operator matching the number of requests
        if data['operator'] == 'SINGLE':
            if len(data['request_set']) > 1:
                raise serializers.ValidationError(
                    _("'Single' type user requests must have exactly one child request.")
                )
        elif len(data['request_set']) == 1:
            raise serializers.ValidationError(
                _("'{}' type user requests must have more than one child request.".format(data['operator'].title()))
            )

        try:
            request_durations = []
            for request in data['request_set']:
                min_window_time = min([window['start'] for window in request['window_set']])
                max_window_time = max([window['end'] for window in request['window_set']])
                tak = get_time_allocation_key(request['location']['telescope_class'],
                                              data['proposal'],
                                              min_window_time,
                                              max_window_time
                                              )
                duration = get_request_duration(request['molecule_set'][0]['instrument_name'],
                                                request['molecule_set'],
                                                request['target'].get('acquire_mode')
                                                )
                request_durations.append((tak, duration))

            total_duration_dict = get_total_duration_dict(data['operator'], request_durations)
            # check the proposal has a time allocation with enough time for all requests depending on operator
            for tak, duration in total_duration_dict.items():
                time_allocation = TimeAllocation.objects.get(
                    semester=tak.semester,
                    telescope_class=tak.telescope_class,
                    proposal=data['proposal'],
                )
                enough_time = False
                if (data['observation_type'] == UserRequest.NORMAL and
                        (time_allocation.std_allocation - time_allocation.std_time_used)) >= (duration / 3600.0):
                    enough_time = True
                elif (data['observation_type'] == UserRequest.TOO and
                        (time_allocation.too_allocation - time_allocation.too_time_used)) >= (duration / 3600.0):
                    enough_time = True
                if not enough_time:
                    raise serializers.ValidationError(
                        _("Proposal {} does not have enough time allocated in semester {} on {} telescopes").format(
                            data['proposal'], tak.semester, tak.telescope_class)
                    )
            # validate the ipp debitting that will take place later
            validate_ipp(data, total_duration_dict)
        except ObjectDoesNotExist:
            raise serializers.ValidationError(_("Time Allocation not found."))
        except TimeAllocationError as e:
            raise serializers.ValidationError(repr(e))

        return data

    def validate_requests(self, value):
        if not value:
            raise serializers.ValidationError(_('You must specify at least 1 request'))
        return value
