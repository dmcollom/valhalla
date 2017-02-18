<template>
  <div id="app">
    <div class="row">
      <div class="col-md-11">
        <alert v-for="alert in alerts" :alertclass="alert.class || 'alert-danger'">{{ alert.msg }}</alert>
      </div>
    </div>
    <div id="tabs">
      <ul class="nav nav-tabs col-md-6">
        <li :class="{ active: tab === 1 }" v-on:click="tab = 1">
          <a title="Observing request form."><i class="fa fa-fw fa-pencil-square-o fa-2x"></i> Form</a>
        </li>
        <li :class="{ active: tab === 2 }" v-on:click="tab = 2">
          <a title="Your observing request displayed in the request API language."><i class="fa fa-fw fa-code fa-2x"></i> Api View</a>
        </li>
        <li :class="{ active: tab === 3 }" v-on:click="tab = 3">
          <a title="Your saved observing requests."><i class="fa fa-fw fa-file-text-o fa-2x"></i> Drafts</a>
        </li>
        <li :class="{ active: tab === 4 }" v-on:click="tab = 4">
          <a title="Help"><i class="fa fa-question fa-fw fa-2x"></i> Help</a>
        </li>
      </ul>
      <div class="col-md-5 panel-actions">
        <span :class="draftId > -1 ? 'btn-group' : ''">
          <button class="btn btn-info" title="Save a draft of this observing request. The request will not be submitted"
                  v-on:click="saveDraft(draftId)">
            <i class="fa fa-save"></i> Save Draft <span v-show="draftId > -1">#{{ draftId }}</span>
          </button>
           <button v-show="draftId > -1" type="button" class="btn btn-info dropdown-toggle" data-toggle="dropdown">
            <span class="caret"></span>
          </button>
          <ul class="dropdown-menu">
            <li><a v-on:click="saveDraft(-1)">Save as new draft</a></li>
          </ul>
        </span>
        <a class="btn btn-success" title="Submit" v-on:click="submit" :disabled="!_.isEmpty(errors)" ><i class="fa fa-check"></i> Submit</a>
      </div>
      <div class="tab-content">
        <div class="tab-pane" :class="{ active: tab === 1 }">
          <div class="row">
            <div class="col-md-11 col-sm-12 col-sm-12">
              <userrequest :errors="errors" :duration_data="duration_data" :userrequest="userrequest"
                           v-on:userrequestupdate="userrequestUpdated"></userrequest>
            </div>
            <div class="col-md-1 hidden-sm hidden-xs">
              <sidenav :userrequest="userrequest" :errors="errors"></sidenav>
            </div>
          </div>
        </div>
        <div class="tab-pane" :class="{ active: tab === 2 }">
          <div class="row">
            <div class="col-md-12">
              <pre>{{ JSON.stringify(userrequest, null, 4) }}</pre>
            </div>
          </div>
        </div>
        <div class="tab-pane" :class="{ active: tab === 3 }">
          <div class="row">
            <div class="col-md-12">
              <drafts v-on:loaddraft="loadDraft" :tab="tab"></drafts>
            </div>
          </div>
        </div>
        <div class="tab-pane" :class="{ active: tab === 4 }">
          <div class="row">
            <div class="col-md-12">
              <h2>Using the compose form</h2>
              <p>
                Use the form to describe the observation you would like carried out on the network.
                Sections marked with an exclamation mark <i class="fa fa-warning text-danger"></i> are incomplete or
                invalid. A complete section will be marked with a <i class="fa fa-check text-success"></i>. Only
                when all sections are marked complete can the observation be submitted.
              </p>
              <p>
                More information about each field may be found by hovering over the field label.
              </p>
              <p>
                Each section may be collapsed for a more compact view. Use the <i class="fa fa-window-minimize"></i>
                and <i class="fa fa-window-maximize"></i> buttons to control the state of the window.
              </p>
              <p>
                Some sections may be copied using the <i class="fa fa-copy"></i> button. This will duplicate
                the section and add it to your observing request. Sections can also be removed using the
                <i class="fa fa-trash"></i> button.
              </p>
              <h2>Using the API view</h2>
              <p>
                This is what your request looks like in JSON format.
              </p>
              <p>
                This code can be used to submit this observation through the Request service API.
                Using the API allows you to generate and submit observations for scheduling using
                programming languages like python.
              </p>
              <p>
                For more information see the
                <a target="_blank" href="https://developers.lco.global/pages/request-service.html">API Documentation</a>
              </p>
              <h2>Loading and saving drafts</h2>
              <p>
                At any time you may save an observation request as a draft. Use the <i class="fa fa-save"></i> Save Draft
                button. Drafts can be loaded and managed from the Drafts pane. You will see drafts saved by other members
                of your proposal as well as your own.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
  import moment from 'moment';
  import _ from 'lodash';
  import $ from 'jquery';
  import Vue from 'vue';

  import userrequest from './components/userrequest.vue';
  import drafts from './components/drafts.vue';
  import sidenav from './components/sidenav.vue';
  import alert from './components/util/alert.vue';
  import {datetimeFormat} from './utils.js';
  export default {
    name: 'app',
    components: {userrequest, drafts, sidenav, alert},
    data: function(){
      return {
        tab: 1,
        draftId: -1,
        userrequest: {
          group_id: '',
          proposal: '',
          ipp_value: 1.05,
          operator: 'SINGLE',
          observation_type: 'NORMAL',
          requests: [{
            target: {
              name: '',
              type: 'SIDEREAL',
              ra: null,
              dec: null,
              proper_motion_ra: 0.0,
              proper_motion_dec: 0.0,
              epoch: 2000,
              parallax: 0,
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
              defocus: 0,
              ag_mode: 'OPTIONAL'
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
        duration_data: {},
        alerts: []
      };
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
            that.duration_data = data.request_durations;
          }
        });
      }, 200),
      submit: function(){
        var that = this;
        $.ajax({
          type: 'POST',
          url: '/api/user_requests/',
          data: JSON.stringify(that.userrequest),
          contentType: 'application/json',
          success: function(data){
            window.location = '/requests/' + data.id;
          }
        });
      },
      userrequestUpdated: function(){
        console.log('userrequest updated');
        this.validate();
      },
      saveDraft: function(id){
        if(!this.userrequest.group_id || !this.userrequest.proposal){
          alert('Please give your draft a title and proposal');
          return;
        }
        var url = '/api/drafts/';
        var method = 'POST';

        if(id > -1){
          url += id + '/';
          method = 'PUT';
        }
        var that = this;
        $.ajax({
          type: method,
          url: url,
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
          for(var error in data.responseJSON.non_field_errors){
            that.alerts.push({class: 'alert-danger', msg: data.responseJSON.non_field_errors[error]});
          }
        });
      },
      loadDraft: function(id){
        this.draftId = id;
        this.tab = 1;
        var that = this;
        $.getJSON('/api/drafts/' + id + '/', function(data){
          that.userrequest = {};
          Vue.nextTick(function() {
            that.userrequest = JSON.parse(data.content);
          });
          that.validate();
        });
      }
    }
  };
  </script>