# -*- coding: utf-8 -*-
#BEGIN_HEADER
from installed_clients.DataFileUtilClient import DataFileUtil
from .utils import report_utils
from .utils.TemplateUtil import TemplateUtil
from .utils.validation_utils import validate_simple_report_params, validate_extended_report_params
import os
from configparser import ConfigParser
#END_HEADER


class KBaseReport:
    '''
    Module Name:
    KBaseReport

    Module Description:
    Module for workspace data object reports, which show the results of running a job in an SDK app.
    '''

    ######## WARNING FOR GEVENT USERS ####### noqa
    # Since asynchronous IO can lead to methods - even the same method -
    # interrupting each other, you must be *very* careful when using global
    # state. A method could easily clobber the state set by another while
    # the latter method is running.
    ######################################### noqa
    VERSION = "3.2.0"
    GIT_URL = "https://github.com/ialarmedalien/KBaseReport"
    GIT_COMMIT_HASH = "f5bc602a97236420844d03782549055d9ecbf2f0"

    #BEGIN_CLASS_HEADER
    #END_CLASS_HEADER

    # config contains contents of config file in a hash or None if it couldn't
    # be found
    def __init__(self, config):
        #BEGIN_CONSTRUCTOR

        self.config = config
        self.callback_url = os.environ['SDK_CALLBACK_URL']
        self.dfu = DataFileUtil(self.callback_url)

        config_parser = ConfigParser()
        config_file = os.environ.get('KB_DEPLOYMENT_CONFIG', None)

        if not config_file:
            raise ValueError('No config file found. Cannot initialise Template Toolkit')

        template_toolkit_config = {}
        config_parser.read(config_file)
        for config_item in config_parser.items('TemplateToolkitPython'):
            template_toolkit_config[config_item[0]] = config_item[1]

        self.config['template_toolkit'] = template_toolkit_config
        self.templater = TemplateUtil(self.config)

        self.scratch = config['scratch']

        #END_CONSTRUCTOR
        pass


    def create(self, ctx, params):
        """
        Function signature for the create() method -- generate a simple,
        text-based report for an app run.
        @deprecated KBaseReport.create_extended_report
        :param params: instance of type "CreateParams" (* Parameters for the
           create() method * * Pass in *either* workspace_name or
           workspace_id -- only one is needed. * Note that workspace_id is
           preferred over workspace_name because workspace_id immutable. If *
           both are provided, the workspace_id will be used. * * Required
           arguments: *     SimpleReport report - See the structure above *
           string workspace_name - Workspace name of the running app.
           Required *         if workspace_id is absent *     int
           workspace_id - Workspace ID of the running app. Required if *
           workspace_name is absent) -> structure: parameter "report" of type
           "SimpleReport" (* A simple report for use in create() * Optional
           arguments: *     string text_message - Readable plain-text report
           message *     string direct_html - Simple HTML text that will be
           rendered within the report widget *     TemplateParams template -
           a template file and template data to be rendered and displayed *
           as HTML. Use in place of 'direct_html' *     list<string> warnings
           - A list of plain-text warning messages *
           list<WorkspaceObject> objects_created - List of result workspace
           objects that this app *         has created. They will get linked
           in the report view) -> structure: parameter "text_message" of
           String, parameter "direct_html" of String, parameter "template" of
           type "TemplateParams" (* Structure representing a template to be
           rendered. 'template_file' must be provided, * 'template_data_json'
           is optional) -> structure: parameter "template_file" of String,
           parameter "template_data_json" of String, parameter "warnings" of
           list of String, parameter "objects_created" of list of type
           "WorkspaceObject" (* Represents a Workspace object with some brief
           description text * that can be associated with the object. *
           Required arguments: *     ws_id ref - workspace ID in the format
           'workspace_id/object_id/version' * Optional arguments: *
           string description - A plaintext, human-readable description of
           the *         object created) -> structure: parameter "ref" of
           type "ws_id" (* Workspace ID reference in the format
           'workspace_id/object_id/version' * @id ws), parameter
           "description" of String, parameter "workspace_name" of String,
           parameter "workspace_id" of Long
        :returns: instance of type "ReportInfo" (* The reference to the saved
           KBaseReport. This is the return object for * both create() and
           create_extended() * Returned data: *    ws_id ref - reference to a
           workspace object in the form of *
           'workspace_id/object_id/version'. This is a reference to a saved *
           Report object (see KBaseReportWorkspace.spec) *    string name -
           Plaintext unique name for the report. In *        create_extended,
           this can optionally be set in a parameter) -> structure: parameter
           "ref" of type "ws_id" (* Workspace ID reference in the format
           'workspace_id/object_id/version' * @id ws), parameter "name" of
           String
        """
        # ctx is the context object
        # return variables are: info
        #BEGIN create
        params = validate_simple_report_params(params)

        if 'template' in params['report']:
            # render template and set content as 'direct_html'
            params['report'] = self.templater.render_template_to_direct_html(params['report'])
        info = report_utils.create_report(params, self.dfu)
        #END create

        # At some point might do deeper type checking...
        if not isinstance(info, dict):
            raise ValueError('Method create return value ' +
                             'info is not type dict as required.')
        # return the results
        return [info]

    def create_extended_report(self, ctx, params):
        """
        Create a report for the results of an app run. This method handles file
        and HTML zipping, uploading, and linking as well as HTML rendering.
        :param params: instance of type "CreateExtendedReportParams" (*
           Parameters used to create a more complex report with file and HTML
           links * * Pass in *either* workspace_name or workspace_id -- only
           one is needed. * Note that workspace_id is preferred over
           workspace_name because workspace_id immutable. * * Note that it is
           possible to pass both 'html_links'/'direct_html_link_index' and
           'direct_html' * as parameters for an extended report; in such
           cases, the file specified by the * 'direct_html_link_links'
           parameter is used for the report and the 'direct_html' is ignored.
           * * Required arguments: *     string workspace_name - Name of the
           workspace where the report *         should be saved. Required if
           workspace_id is absent *     int workspace_id - ID of workspace
           where the report should be saved. *         Required if
           workspace_name is absent * Optional arguments: *     string
           message - Simple text message to store in the report object *
           list<WorkspaceObject> objects_created - List of result workspace
           objects that this app *         has created. They will be linked
           in the report view *     list<string> warnings - A list of
           plain-text warning messages *     string direct_html - Simple HTML
           text content to be rendered within the report widget. *
           Set only one of 'direct_html', 'template', and
           'html_links'/'direct_html_link_index'. *         Setting both
           'template' and 'direct_html' will generate an error. *
           TemplateParams template - render a template to produce HTML text
           content that will be *         rendered within the report widget.
           Setting 'template' and 'direct_html' or *
           'html_links'/'direct_html_link_index' will generate an error. *
           list<File> html_links - A list of paths, shock IDs, or template
           specs pointing to HTML files or directories. *         If you pass
           in paths to directories, they will be zipped and uploaded *
           int direct_html_link_index - Index in html_links to set the
           direct/default view in the report. *         Set only one of
           'direct_html', 'template', and
           'html_links'/'direct_html_link_index'. *         Setting both
           'template' and 'html_links'/'direct_html_link_index' will generate
           an error. *     list<File> file_links - Allows the user to specify
           files that the report widget *         should link for download.
           If you pass in paths to directories, they will be zipped. *
           Each entry should be a path, shock ID, or template specification.
           *     string report_object_name - Name to use for the report
           object (will *         be auto-generated if unspecified) *
           html_window_height - Fixed height in pixels of the HTML window for
           the report *     summary_window_height - Fixed height in pixels of
           the summary window for the report) -> structure: parameter
           "message" of String, parameter "objects_created" of list of type
           "WorkspaceObject" (* Represents a Workspace object with some brief
           description text * that can be associated with the object. *
           Required arguments: *     ws_id ref - workspace ID in the format
           'workspace_id/object_id/version' * Optional arguments: *
           string description - A plaintext, human-readable description of
           the *         object created) -> structure: parameter "ref" of
           type "ws_id" (* Workspace ID reference in the format
           'workspace_id/object_id/version' * @id ws), parameter
           "description" of String, parameter "warnings" of list of String,
           parameter "html_links" of list of type "File" (* A file to be
           linked in the report. Pass in *either* a shock_id or a * path. If
           a path to a file is given, then the file will be uploaded. If a *
           path to a directory is given, then it will be zipped and uploaded.
           * Required arguments: *     string name - Plain-text filename (eg.
           "results.zip") -- shown to the user *  One of the following
           identifiers is required: *     string path - Can be a file or
           directory path. *     string shock_id - Shock node ID. *
           TemplateParams template - template to be rendered and saved as a
           file. * Optional arguments: *     string label - A short
           description for the file (eg. "Filter results") *     string
           description - A more detailed, human-readable description of the
           file) -> structure: parameter "path" of String, parameter
           "shock_id" of String, parameter "template" of type
           "TemplateParams" (* Structure representing a template to be
           rendered. 'template_file' must be provided, * 'template_data_json'
           is optional) -> structure: parameter "template_file" of String,
           parameter "template_data_json" of String, parameter "name" of
           String, parameter "label" of String, parameter "description" of
           String, parameter "template" of type "TemplateParams" (* Structure
           representing a template to be rendered. 'template_file' must be
           provided, * 'template_data_json' is optional) -> structure:
           parameter "template_file" of String, parameter
           "template_data_json" of String, parameter "direct_html" of String,
           parameter "direct_html_link_index" of Long, parameter "file_links"
           of list of type "File" (* A file to be linked in the report. Pass
           in *either* a shock_id or a * path. If a path to a file is given,
           then the file will be uploaded. If a * path to a directory is
           given, then it will be zipped and uploaded. * Required arguments:
           *     string name - Plain-text filename (eg. "results.zip") --
           shown to the user *  One of the following identifiers is required:
           *     string path - Can be a file or directory path. *     string
           shock_id - Shock node ID. *     TemplateParams template - template
           to be rendered and saved as a file. * Optional arguments: *
           string label - A short description for the file (eg. "Filter
           results") *     string description - A more detailed,
           human-readable description of the file) -> structure: parameter
           "path" of String, parameter "shock_id" of String, parameter
           "template" of type "TemplateParams" (* Structure representing a
           template to be rendered. 'template_file' must be provided, *
           'template_data_json' is optional) -> structure: parameter
           "template_file" of String, parameter "template_data_json" of
           String, parameter "name" of String, parameter "label" of String,
           parameter "description" of String, parameter "report_object_name"
           of String, parameter "html_window_height" of Double, parameter
           "summary_window_height" of Double, parameter "workspace_name" of
           String, parameter "workspace_id" of Long
        :returns: instance of type "ReportInfo" (* The reference to the saved
           KBaseReport. This is the return object for * both create() and
           create_extended() * Returned data: *    ws_id ref - reference to a
           workspace object in the form of *
           'workspace_id/object_id/version'. This is a reference to a saved *
           Report object (see KBaseReportWorkspace.spec) *    string name -
           Plaintext unique name for the report. In *        create_extended,
           this can optionally be set in a parameter) -> structure: parameter
           "ref" of type "ws_id" (* Workspace ID reference in the format
           'workspace_id/object_id/version' * @id ws), parameter "name" of
           String
        """
        # ctx is the context object
        # return variables are: info
        #BEGIN create_extended_report
        params = validate_extended_report_params(params)
        if 'template' in params:
            # render template and set content as 'direct_html'
            params = self.templater.render_template_to_direct_html(params)
        info = report_utils.create_extended(params, self.dfu, self.templater)
        #END create_extended_report

        # At some point might do deeper type checking...
        if not isinstance(info, dict):
            raise ValueError('Method create_extended_report return value ' +
                             'info is not type dict as required.')
        # return the results
        return [info]

    def render_template(self, ctx, params):
        """
        Render a file from a template. This method takes a template file and
        a data structure, renders the template, and saves the results to a file.
        It returns the output file path in the form
        { 'path': '/path/to/file' }
        To ensure that the template and the output file are accessible to both
        the KBaseReport service and the app requesting the template rendering, the
        template file should be copied into the shared `scratch` directory and the
        output_file location should also be in `scratch`.
        See https://github.com/kbaseIncubator/kbase_report_templates for sample
        page templates, standard includes, and instructions on creating your own
        templates.
        :param params: instance of type "RenderTemplateParams" (* Render a
           template using the supplied data, saving the results to an output
           * file in the scratch directory. * * Required arguments: *
           string template_file  -  Path to the template file to be rendered.
           *     string output_file    -  Path to the file where the rendered
           template *                              should be saved. Must be
           in the scratch directory. * Optional: *     string
           template_data_json -  Data for rendering in the template.) ->
           structure: parameter "template_file" of String, parameter
           "output_file" of String, parameter "template_data_json" of String
        :returns: instance of type "File" (* A file to be linked in the
           report. Pass in *either* a shock_id or a * path. If a path to a
           file is given, then the file will be uploaded. If a * path to a
           directory is given, then it will be zipped and uploaded. *
           Required arguments: *     string name - Plain-text filename (eg.
           "results.zip") -- shown to the user *  One of the following
           identifiers is required: *     string path - Can be a file or
           directory path. *     string shock_id - Shock node ID. *
           TemplateParams template - template to be rendered and saved as a
           file. * Optional arguments: *     string label - A short
           description for the file (eg. "Filter results") *     string
           description - A more detailed, human-readable description of the
           file) -> structure: parameter "path" of String, parameter
           "shock_id" of String, parameter "template" of type
           "TemplateParams" (* Structure representing a template to be
           rendered. 'template_file' must be provided, * 'template_data_json'
           is optional) -> structure: parameter "template_file" of String,
           parameter "template_data_json" of String, parameter "name" of
           String, parameter "label" of String, parameter "description" of
           String
        """
        # ctx is the context object
        # return variables are: output_file_path
        #BEGIN render_template
        output_file_path = self.templater.render_template_to_file(params)
        #END render_template

        # At some point might do deeper type checking...
        if not isinstance(output_file_path, dict):
            raise ValueError('Method render_template return value ' +
                             'output_file_path is not type dict as required.')
        # return the results
        return [output_file_path]

    def render_templates(self, ctx, params):
        """
        Render files from a set of template specifications.
        It returns the output file paths in the order they were supplied in the form
        [{ 'path': '/path/to/file' }, { 'path': '/path/to/file2' }, ....]
        If any template fails to render, the endpoint will return an error.
        :param params: instance of type "RenderTemplateListParams" ->
           structure: parameter "params" of list of type
           "RenderTemplateParams" (* Render a template using the supplied
           data, saving the results to an output * file in the scratch
           directory. * * Required arguments: *     string template_file  -
           Path to the template file to be rendered. *     string output_file
           -  Path to the file where the rendered template *
           should be saved. Must be in the scratch directory. * Optional: *
           string template_data_json -  Data for rendering in the template.)
           -> structure: parameter "template_file" of String, parameter
           "output_file" of String, parameter "template_data_json" of String
        :returns: instance of type "FileList" -> structure: parameter
           "file_list" of list of type "File" (* A file to be linked in the
           report. Pass in *either* a shock_id or a * path. If a path to a
           file is given, then the file will be uploaded. If a * path to a
           directory is given, then it will be zipped and uploaded. *
           Required arguments: *     string name - Plain-text filename (eg.
           "results.zip") -- shown to the user *  One of the following
           identifiers is required: *     string path - Can be a file or
           directory path. *     string shock_id - Shock node ID. *
           TemplateParams template - template to be rendered and saved as a
           file. * Optional arguments: *     string label - A short
           description for the file (eg. "Filter results") *     string
           description - A more detailed, human-readable description of the
           file) -> structure: parameter "path" of String, parameter
           "shock_id" of String, parameter "template" of type
           "TemplateParams" (* Structure representing a template to be
           rendered. 'template_file' must be provided, * 'template_data_json'
           is optional) -> structure: parameter "template_file" of String,
           parameter "template_data_json" of String, parameter "name" of
           String, parameter "label" of String, parameter "description" of
           String
        """
        # ctx is the context object
        # return variables are: output_paths
        #BEGIN render_templates
        output_paths = self.templater.render_template_list_to_files(params)
        #END render_templates

        # At some point might do deeper type checking...
        if not isinstance(output_paths, list):
            raise ValueError('Method render_templates return value ' +
                             'output_paths is not type dict as required.')
        # return the results
        return [output_paths]
    def status(self, ctx):
        #BEGIN_STATUS
        returnVal = {'state': "OK",
                     'message': "",
                     'version': self.VERSION,
                     'git_url': self.GIT_URL,
                     'git_commit_hash': self.GIT_COMMIT_HASH}
        #END_STATUS
        return [returnVal]
