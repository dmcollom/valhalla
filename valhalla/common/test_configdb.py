
configdb_data = [
    {
        'code': 'tst',
        'enclosure_set': [
            {
                'code': 'doma',
                'telescope_set': [
                    {
                        'code': '1m0a',
                        'lat': -32.3805542,
                        'long': 20.8100352,
                        'horizon': 15.0,
                        'ha_limit_pos': 4.6,
                        'ha_limit_neg': -4.6,
                        'instrument_set': [
                            {
                                'state': 'SCHEDULABLE',
                                'code': 'xx01',
                                'science_camera': {
                                    'camera_type': {
                                        'code': '1M0-SCICAM-SBIG',
                                        'name': '1M0-SCICAM-SBIG',
                                        'default_mode': {
                                            'binning': 2,
                                            'readout': 14.5,
                                        },
                                        'config_change_time': 0,
                                        'acquire_processing_time': 0,
                                        'acquire_exposure_time': 0,
                                        'front_padding': 90,
                                        'filter_change_time': 2,
                                        'fixed_overhead_per_exposure': 1,
                                        'mode_set': [
                                            {
                                                'binning': 1,
                                                'readout': 35.0,
                                            },
                                            {
                                                'binning': 2,
                                                'readout': 14.5,
                                            },
                                            {
                                                'binning': 3,
                                                'readout': 11.5,
                                            },
                                        ]
                                    },
                                    'filters': 'air',
                                },
                                '__str__': 'tst.doma.1m0a.xx01-xx01',
                            },
                            {
                                'state': 'SCHEDULABLE',
                                'code': 'xx02',
                                'science_camera': {
                                    'camera_type': {
                                        'code': '2M0-FLOYDS-SCICAM',
                                        'name': '2M0-FLOYDS-SCICAM',
                                        'config_change_time': 30,
                                        'acquire_processing_time': 60,
                                        'acquire_exposure_time': 30,
                                        'front_padding': 240,
                                        'filter_change_time': 0,
                                        'fixed_overhead_per_exposure': 0.5,
                                        'default_mode': {
                                            'binning': 1,
                                            'readout': 25,
                                        },
                                        'mode_set': [
                                            {
                                                'binning': 1,
                                                'readout': 25,
                                            },
                                        ]
                                    },
                                    'filters': 'slit_1.2as,floyds_slit_default',
                                },
                                '__str__': 'tst.doma.1m0a.xx02-xx02',
                            },
                        ]
                    },
                ]
            },
            {
                'code': 'domb',
                'telescope_set': [
                    {
                        'code': '1m0a',
                        'lat': -32.3805542,
                        'long': 20.8100352,
                        'horizon': 15.0,
                        'ha_limit_pos': 4.6,
                        'ha_limit_neg': -4.6,
                        'instrument_set': [
                            {
                                'state': 'SCHEDULABLE',
                                'code': 'xx03',
                                'science_camera': {
                                    'camera_type': {
                                        'code': '1M0-SCICAM-SBIG',
                                        'name': '1M0-SCICAM-SBIG',
                                        'default_mode': {
                                            'binning': 2,
                                            'readout': 14.5,
                                        },
                                        'config_change_time': 0,
                                        'acquire_processing_time': 0,
                                        'acquire_exposure_time': 0,
                                        'front_padding': 90,
                                        'filter_change_time': 2,
                                        'fixed_overhead_per_exposure': 1,
                                        'mode_set': [
                                            {
                                                'binning': 1,
                                                'readout': 35.0,
                                            },
                                            {
                                                'binning': 2,
                                                'readout': 14.5,
                                            },
                                            {
                                                'binning': 3,
                                                'readout': 11.5,
                                            },
                                        ]
                                    },
                                    'filters': 'air',
                                },
                                '__str__': 'tst.domb.1m0a.xx01-xx01',
                            },
                            {
                                'state': 'SCHEDULABLE',
                                'code': 'xx04',
                                'science_camera': {
                                    'camera_type': {
                                        'code': '2M0-FLOYDS-SCICAM',
                                        'name': '2M0-FLOYDS-SCICAM',
                                        'config_change_time': 30,
                                        'acquire_processing_time': 60,
                                        'acquire_exposure_time': 30,
                                        'front_padding': 240,
                                        'filter_change_time': 0,
                                        'fixed_overhead_per_exposure': 0.5,
                                        'default_mode': {
                                            'binning': 1,
                                            'readout': 25,
                                        },
                                        'mode_set': [
                                            {
                                                'binning': 1,
                                                'readout': 25,
                                            },
                                        ]
                                    },
                                    'filters': 'slit_1.2as,floyds_slit_default',
                                },
                                '__str__': 'tst.domb.1m0a.xx02-xx02',
                            },
                        ]
                    },
                ]
            },
        ]
    },
    {
        'code': 'non',
        'enclosure_set': [
            {
                'code': 'doma',
                'telescope_set': [
                    {
                        'code': '1m0a',
                        'lat': -32.3805542,
                        'long': 20.8100352,
                        'horizon': 15.0,
                        'ha_limit_pos': 4.6,
                        'ha_limit_neg': -4.6,
                        'instrument_set': [
                        ]
                    },
                ]
            },
        ]
    },
]
