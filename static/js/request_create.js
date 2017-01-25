/* globals _ $ Vue moment */

var datetimeFormat = 'YYYY-M-D HH:mm:ss';

var instrumentTypeMap = {
  '2M0-SCICAM-SPECTRAL': {type: 'IMAGE', class: '2m0', filters: [], binnings: [], default_binning: null},
  '2M0-FLOYDS-SCICAM': {type: 'SPECTRA', class: '2m0', filters: [], binnings: [], default_binning: null},
  '0M8-SCICAM-SBIG': {type: 'IMAGE', class: '0m8', filters: [], binnings: [], default_binning: null},
  '1M0-SCICAM-SINISTRO': {type: 'IMAGE', class: '1m0', filters: [], binnings: [], default_binning: null},
  '0M4-SCICAM-SBIG': {type: 'IMAGE', class: '0m4', filters: [], binnings: [], default_binning: null},
  '0M8-NRES-SCICAM': {type: 'SPECTRA', class: '0m8', filters: [], binnings: [], default_binning: null}
};

var collapseMixin = {
  watch: {
    parentshow: function(value){
      this.show = value;
    }
  }
};

Vue.component('userrequest', {
  props: ['errors', 'iuserrequest'],
  data: function(){
    var initial = _.cloneDeep(this.iuserrequest);
    initial.show = true;
    return initial;
  },
  created: function(){
    var that = this;
    $.getJSON('/api/profile/', function(data){
      that.proposals = data.proposals;
      that.available_instruments = data.available_instrument_types;
      that.update();
    });
  },
  computed:{
    toRep: function(){
      var rep = {};
      var that = this;
      ['group_id', 'proposal', 'operator', 'ipp_value', 'observation_type', 'requests'].forEach(function(x){
        rep[x] = that[x];
      });
      return rep;
    },
    proposalOptions: function(){
      return _.map(this.proposals, function(p){return {'value': p, 'text': p};});
    },
    operator: function(){
      return this.requests.length > 1 ? 'MANY' : 'SINGLE';
    }
  },
  methods: {
    update: function(){
      this.$emit('userrequestupdate', this.toRep);
    },
    requestUpdated: function(data){
      console.log('request updated');
      Vue.set(this.requests, data.id, data.data);
      this.update();
    },
    addRequest: function(idx){
      var newRequest = _.cloneDeep(this.requests[idx]);
      this.requests.push(newRequest);
      this.update();
    },
    removeRequest: function(idx){
      this.requests.splice(idx, 1);
      this.update();
    }
  },
  watch: {
    iuserrequest: function(value){
      Object.assign(this.$data, value);
    }
  },
  template: '#userrequest-template'
});

Vue.component('request', {
  props: ['irequest', 'index', 'errors', 'iavailable_instruments', 'parentshow'],
  mixins: [collapseMixin],
  data: function(){
    var initial = _.cloneDeep(this.irequest);
    initial.show = true;
    return initial;
  },
  computed: {
    toRep: function(){
      var rep = {};
      var that = this;
      ['target', 'molecules', 'windows', 'location', 'constraints', 'data_type', 'instrument_name'].forEach(function(x){
        rep[x] = that[x];
      });
      return rep;
    },
    availableInstrumentOptions: function(){
      var options = [];
      for(var i in this.iavailable_instruments){
        var instrument_name = this.iavailable_instruments[i];
        if(instrumentTypeMap[instrument_name].type === this.data_type){
          options.push({value: instrument_name, text: instrument_name});
        }
      }
      return options;
    },
    firstAvailableInstrument: function(){
      return this.availableInstrumentOptions[0].value;
    }
  },
  watch: {
    data_type: function(){
      if(instrumentTypeMap[this.instrument_name].type != this.data_type){
        this.instrument_name = this.firstAvailableInstrument;
        this.update();
      }
    },
    instrument_name: function(value){
      if(value){
        this.location.telescope_class = vm.instrumentTypeMap[value].class;
        $.getJSON('/api/instrument/' + value + '/', function(data){
          vm.instrumentTypeMap[value].filters = data.filters;
          vm.instrumentTypeMap[value].binnings = data.binnings;
          vm.instrumentTypeMap[value].default_binning = data.default_binning;
        });
      }
    },
    irequest: function(value){
      Object.assign(this.$data, value);
    },
    iavailable_instruments: function(){
      if(!this.instrument_name){
        this.instrument_name = this.firstAvailableInstrument;
      }
    }
  },
  methods: {
    update: function(){
      this.$emit('requestupdate', {'id': this.index, 'data': this.toRep});
    },
    moleculeUpdated: function(data){
      Vue.set(this.molecules, data.id, data.data);
      console.log('moleculeupdated');
      this.update();
    },
    windowUpdated: function(data){
      Vue.set(this.windows, data.id, data.data);
      console.log('windowUpdated');
      this.update();
    },
    targetUpdated: function(data){
      this.target = data.data;
      console.log('targetUpdated');
      this.update();
    },
    constraintsUpdated: function(data){
      this.constraints = data.data;
      console.log('constraintsUpdated');
      this.update();
    },
    addWindow: function(idx){
      var newWindow = JSON.parse(JSON.stringify(this.windows[idx]));
      this.windows.push(newWindow);
      this.update();
    },
    addMolecule: function(idx){
      var newMolecule = JSON.parse(JSON.stringify(this.molecules[idx]));
      this.molecules.push(newMolecule);
      this.update();
    },
    removeWindow: function(idx){
      this.windows.splice(idx, 1);
      this.update();
    },
    removeMolecule: function(idx){
      this.molecules.splice(idx, 1);
      this.update();
    }
  },
  template: '#request-template'
});

Vue.component('molecule', {
  props: ['imolecule', 'index', 'errors', 'selectedinstrument', 'datatype', 'parentshow'],
  mixins: [collapseMixin],
  data: function(){
    var initial = _.cloneDeep(this.imolecule);
    initial.show = true;
    return initial;
  },
  computed: {
    toRep: function(){
      var rep = {};
      var that = this;
      var fields = ['filter', 'bin_x', 'bin_y', 'exposure_count', 'exposure_time', 'instrument_name', 'type'];
      if(this.datatype === 'SPECTRUM'){
        fields = fields.concat(['acquire_radius_arcsec', 'acquire_mode']);
      }
      fields.forEach(function(x){
        rep[x] = that[x];
      });
      return rep;
    },
    filterOptions: function(){
      var options = [{value: '', text: ''}];
      var filters = _.get(this.$root.instrumentTypeMap, [this.selectedinstrument, 'filters'], []);
      for(var filter in filters){
        if(['Standard', 'Slit', 'VirtualSlit'].indexOf(filters[filter].type) > -1){ // TODO select on mode
          options.push({value: filter, text: filters[filter].name});
        }
      }
      return options;
    },
    binningsOptions: function(){
      var options = [];
      var binnings = _.get(this.$root.instrumentTypeMap, [this.selectedinstrument, 'binnings'], []);
      binnings.forEach(function(binning){
        options.push({value: binning, text: binning});
      });
      return options;
    },
  },
  methods: {
    update: function(){
      this.$emit('moleculeupdate', {'id': this.index, 'data': this.toRep});
    },
    binningsUpdated: function(){
      this.bin_y = this.bin_x;
      this.update();
    }
  },
  watch: {
    selectedinstrument: function(value){
      this.instrument_name = value;
      this.filter = '';
      // wait for options to update, then set default
      var that = this;
      setTimeout(function(){
        var default_binning = _.get(that.$root.instrumentTypeMap, [that.selectedinstrument, 'default_binning'], null);
        that.bin_x = default_binning;
        that.bin_y = default_binning;
        that.update();
      }, 100);
    },
    datatype: function(value){
      this.type = (value === 'IMAGE') ? 'EXPOSE': 'SPECTRUM';
    },
    imolecule: function(value){
      Object.assign(this.$data, value);
    }
  },
  template: '#molecule-template'
});

Vue.component('target', {
  props: ['itarget', 'errors', 'datatype', 'parentshow'],
  mixins: [collapseMixin],
  data: function(){
    var initial = _.cloneDeep(this.itarget);
    initial.show = true;
    initial.lookingUP = false;
    return initial;
  },
  computed: {
    toRep: function(){
      var rep = {'name': this.name, 'type': this.type};
      var that = this;
      if(this.type === 'SIDEREAL'){
        ['ra', 'dec', 'proper_motion_ra', 'proper_motion_dec', 'epoch', 'parallax'].forEach(function(x){
          rep[x] = that[x];
        });
      }else if(this.type === 'NON_SIDEREAL'){
        ['scheme', 'epoch', 'orbinc', 'longascnode', 'argofperih', 'meandist', 'eccentricity', 'meananom'].forEach(function(x){
          rep[x] = that[x];
        });
      }
      if(this.datatype === 'SPECTRA'){
        ['rot_mode', 'rot_angle'].forEach(function(x){
          rep[x] = that[x];
        });
      }
      return rep;
    }
  },
  methods: {
    update: function(){
      this.$emit('targetupdate', {'data': this.toRep});
    }
  },
  watch: {
    name: _.debounce(function(name){
      this.lookingUP = true;
      var that = this;
      $.getJSON('https://lco.global/lookUP/json/?name=' + name).done(function(data){
        that.ra = data.ra.decimal;
        that.dec = data.dec.decimal;
        that.proper_motion_ra = data.pmra;
        that.proper_motion_dec = data.pmdec;
        that.update();
      }).always(function(){
        that.lookingUP = false;
      });
    }, 500),
    itarget: function(value){
      Object.assign(this.$data, value);
    }
  },
  template: '#target-template'
});

Vue.component('window', {
  props: ['iwindow', 'index', 'errors', 'parentshow'],
  mixins: [collapseMixin],
  data: function(){
    var initial = _.cloneDeep(this.iwindow);
    initial.show = true;
    return initial;
  },
  computed: {
    toRep: function(){
      return {'start': this.start, 'end': this.end};
    }
  },
  methods: {
    update: function(){
      this.$emit('windowupdate', {'id': this.index, 'data': this.toRep});
    }
  },
  watch: {
    iwindow: function(value){
      Object.assign(this.$data, value);
    }
  },
  template: '#window-template'
});

Vue.component('constraints', {
  props: ['iconstraints', 'errors', 'parentshow'],
  mixins: [collapseMixin],
  data: function(){
    var initial = _.cloneDeep(this.iconstraints);
    initial.show = true;
    return initial;
  },
  computed: {
    toRep: function(){
      return {'max_airmass': this.max_airmass, 'min_lunar_distance': this.min_lunar_distance};
    }
  },
  methods: {
    update: function(){
      this.$emit('constraintsupdate', {'data': this.toRep});
    }
  },
  watch: {
    iconstraints: function(value){
      Object.assign(this.$data, value);
    }
  },
  template: '#constraints-template'
});

Vue.component('custom-field', {
  props: ['value', 'label', 'field', 'errors', 'type'],
  mounted: function(){
    if(this.type === 'datetime'){
      var that = this;
      $('#' + this.field).datetimepicker({
        format: datetimeFormat,
        minDate: moment().subtract(1, 'days'),
        keyBinds: {left: null, right: null, up: null, down: null}
      }).on('dp.change', function(e){
        that.update(moment(e.date).format(datetimeFormat));
      });
    }
  },
  methods: {
    update: function(value){
      this.$emit('input', value);
    }
  },
  template: '#custom-field'
});

Vue.component('custom-select', {
  props: ['value', 'label', 'field', 'options', 'errors'],
  methods: {
    update: function(value){
      this.$emit('input', value);
    },
    isSelected: function(option){
      return option === this.value;
    }
  },
  template: '#custom-select'
});

Vue.component('sidenav', {
  props: ['userrequest'],
  template: '#sidenav-template'
});

Vue.component('drafts', {
  props: ['tab'],
  data: function(){
    return {'drafts': []};
  },
  methods: {
    fetchDrafts: function(){
      var that = this;
      $.getJSON('/api/drafts/', function(data){
        that.drafts = data.results;
      });
    },
    loadDraft: function(id){
      this.$emit('loaddraft', id);
    }
  },
  watch: {
    tab: function(value){
      if(value === 3) this.fetchDrafts();
    }
  },
  template: '#drafts-template'
});

Vue.component('alert', {
  props: ['alertclass'],
  template: '#alert-template'
});

var vm = new Vue({
  el: '#vueapp',
  data:{
    tab: 1,
    draftId: -1,
    duration: 0,
    instrumentTypeMap: instrumentTypeMap,
    userrequest: {
      show: true,
      proposals: [],
      available_instruments: [],
      group_id: '',
      proposal: '',
      ipp_value: 1.05,
      observation_type: 'NORMAL',
      requests: [{
        data_type: 'IMAGE',
        instrument_name: '',
        target: {
          name: '',
          type: 'SIDEREAL',
          ra: 0,
          dec: 0,
          scheme: 'MPC_MINOR_PLANET',
          proper_motion_ra: 0.0,
          proper_motion_dec: 0.0,
          epoch: 2000,
          parallax: 0,
          orbinc: 0,
          longascnode: 0,
          argofperih: 0,
          meandist: 0,
          eccentricity: 0,
          meananom: 0,
          rot_mode: 'SKY',
          rot_angle: 0
        },
        molecules:[{
          type: 'EXPOSE',
          instrument_name: '',
          filter: '',
          exposure_time: 30,
          exposure_count: 1,
          bin_x: null,
          bin_y: null,
          fill_window: false,
          acquire_mode: 'OFF',
          acquire_radius_arcsec: null,
        }],
        windows:[{
          start: moment().format(datetimeFormat),
          end: moment().format(datetimeFormat)
        }],
        location:{
          telescope_class: ''
        },
        constraints: {
          max_airmass: 2.0,
          min_lunar_distance: 30.0
        }
      }]
    },
    errors: {},
    alerts: []
  },
  computed: {
    durationDisplay: function(){
      var duration =  moment.duration(this.duration, 'seconds');
      return duration.hours() + ' hours ' + duration.minutes() + ' minutes ' + duration.seconds() + ' seconds';
    }
  },
  methods: {
    validate: _.debounce(function(){
      var that = this;
      $.ajax({
        type: 'POST',
        url: '/api/user_requests/validate/',
        data: JSON.stringify(that.userrequest),
        contentType: 'application/json',
        success: function(data){
          that.errors = data.errors;
          that.duration = data.duration;
        }
      });
    }, 200),
    userrequestUpdated: function(data){
      console.log('userrequest updated');
      this.userrequest = data;
      this.validate();
    },
    saveDraft: function(){
      if(!this.userrequest.group_id || !this.userrequest.proposal){
        alert('Please give your draft a title and proposal');
        return;
      }
      var that = this;
      $.ajax({
        type: 'POST',
        url: '/api/drafts/',
        data: JSON.stringify({
          proposal: that.userrequest.proposal,
          title: that.userrequest.group_id,
          content: JSON.stringify(that.userrequest)
        }),
        contentType: 'application/json',
      }).done(function(data){
        that.draftId = data.id;
        that.alerts.push({class: 'alert-success', msg: 'Draft id: ' + data.id + ' saved successfully.' });
        console.log('Draft saved ' + that.draftId);
      }).fail(function(data){
        that.alerts.push({class: 'alert-danger', msg: data.responseJSON.non_field_errors[0] });
      });
    },
    loadDraft: function(id){
      this.draftId = id;
      this.tab = 1;
      var that = this;
      $.getJSON('/api/drafts/' + id + '/', function(data){
        that.userrequest = JSON.parse(data.content);
      });
    }
  }
});

$('body').scrollspy({
  target: '.bs-docs-sidebar',
  offset: 180
});
