# -*- coding: utf-8 -*-
import contextlib
import json
import os
import re
import unittest

from configparser import ConfigParser
from template import Template
from template.util import TemplateException
from uuid import uuid4

from KBaseReport.KBaseReportImpl import KBaseReport
from KBaseReport.utils.TemplateUtil import TemplateUtil
from KBaseReport.utils.validation_utils import validate_template_params


def get_test_data():

    TEMPLATE_DIR = os.environ.get('TEMPLATE_DIR', '/kb/module/kbase_report_templates')
    APP_DIR = os.environ.get('APP_DIR', '/kb/module')

    TEST_DATA = {
        'template_dir': TEMPLATE_DIR,

        'title': {
            'page_title': 'My First Template'
        },
        'content': {
            'value': ['this', 'that', 'the other']
        },

        'template_file': 'views/test/test_template.tt',
        'scratch': '/kb/module/work/tmp',

        'template_toolkit_config': {
            'ABSOLUTE': 1,
            'RELATIVE': 1,
            'INCLUDE_PATH': TEMPLATE_DIR + ':' + os.path.join(TEMPLATE_DIR, 'views')
        },
    }

    TEST_DATA['title_json'] = json.dumps(TEST_DATA['title'])
    TEST_DATA['content_json'] = json.dumps(TEST_DATA['content'])

    TEST_DATA['template'] = os.path.join(TEMPLATE_DIR, TEST_DATA['template_file'])

    TEST_DATA['output_file'] = os.path.join(TEST_DATA['scratch'], 'outfile.txt')
    TEST_DATA['output_file_with_dirs'] = os.path.join(TEST_DATA['scratch'], 'path', 'to', 'out.txt')

    # set up the rendering test ref data
    TEST_DATA['render_test'] = {}
    for type in [None, 'title', 'content']:
        type_str = 'None' if type is None else type
        rendered_file_path = os.path.join(APP_DIR, 'test/data/tmpl_output_' + type_str + '.txt')

        with open(rendered_file_path, 'r') as f:
            rendered_text = f.read()

        TEST_DATA['render_test'][type] = {
            'abs_path': rendered_text.rstrip(),
            'rel_path': rendered_text.rstrip().replace(
                TEST_DATA['template'], TEST_DATA['template_file']
            ),
        }

    return TEST_DATA


TEST_DATA = get_test_data()


@contextlib.contextmanager
def modified_environ(*remove, **update):
    """
    Temporarily updates the ``os.environ`` dictionary in-place.

    The ``os.environ`` dictionary is updated in-place so that the modification
    is sure to work in all situations.

    :param remove: Environment variables to remove.
    :param update: Dictionary of environment variables and values to add/update.
    """
    env = os.environ
    update = update or {}
    remove = remove or []

    # List of environment variables being updated or removed.
    stomped = (set(update.keys()) | set(remove)) & set(env.keys())
    # Environment variables and values to restore on exit.
    update_after = {k: env[k] for k in stomped}
    # Environment variables and values to remove on exit.
    remove_after = frozenset(k for k in update if k not in env)

    try:
        env.update(update)
        [env.pop(k, None) for k in remove]
        yield
    finally:
        env.update(update_after)
        [env.pop(k) for k in remove_after]


class TestTemplateUtils(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        config_file = os.environ.get('KB_DEPLOYMENT_CONFIG', None)
        cls.cfg = {}
        cls.cfg_ttp = {}
        if not config_file:
            cls.cfg = {
                'scratch': TEST_DATA['scratch'],
                'template_toolkit': TEST_DATA['template_toolkit_config'],
            }
            cls.cfg_ttp = TEST_DATA['template_toolkit_config']
        else:
            config = ConfigParser()
            config.read(config_file)
            for nameval in config.items('KBaseReport'):
                cls.cfg[nameval[0]] = nameval[1]

            for nameval in config.items('TemplateToolkitPython'):
                cls.cfg_ttp[nameval[0]] = nameval[1]

        cls.scratch = cls.cfg['scratch']
        cls.serviceImpl = KBaseReport(cls.cfg)
        cls.templateUtil = TemplateUtil(cls.cfg)

    def getImpl(self):
        return self.__class__.serviceImpl

    def getTmpl(self):
        return self.__class__.templateUtil

    def get_input_set(self):

        input_set = [
            # config errors
            {
                'desc': 'no conf - fails on the lack of a required field',
                'regex': 'scratch.*?required field',
                'config': {},
            },
            {
                'desc': 'wrong format for tt params',
                'regex': 'must be of dict type',
                'config': {
                    'template_toolkit': 'is a super cool templating library',
                }
            },
            {
                'desc': 'invalid scratch dir',
                'regex': 'scratch.*?does not exist on filesystem',
                'config': {
                    'scratch': '/does/not/exist',
                }
            },
            #   input errors
            {
                'desc': 'missing required param',
                'regex': "required field",
                'params': {},
            },
            {
                'desc': 'template file is wrong type',
                'regex': "must be of string type",
                'params': {
                    'template_file': {
                        'path': '/does/not/exist'
                    },
                }
            },
            {
                'desc': 'invalid JSON',
                'regex': "Invalid JSON",
                'params': {
                    'template_data_json': '"this is not valid JSON',
                }
            },
            {
                'desc': 'invalid JSON',
                'regex': "Invalid JSON",
                'params': {
                    'template_data_json': '["this",{"is":"not"},{"valid":"json"]',
                }
            },
            {
                'desc': 'output file is not in scratch dir',
                'regex': "not in the scratch directory",
                'params': {
                    'output_file': 'path/to/file',
                }
            },
        ]

        valid = {
            'params': {
                'output_file': TEST_DATA['output_file'],
                'template_file': TEST_DATA['template'],
            },
            'config': self.cfg
        }
        valid['config']['template_toolkit'] = self.cfg_ttp

        for item in input_set:
            for facet in ['params', 'config']:
                if facet not in item:
                    item[facet] = valid[facet]
                elif len(item[facet]) > 0:
                    item['err_field'] = [facet + '.' + key for key in item[facet].keys()]
                    temp = { **valid[facet], **item[facet] }
                    item[facet] = temp

        return input_set

    def _title_check_rendering(self, string, has_title=False):
        no_title_compiled = re.compile('<title></title>')
        title_compiled = re.compile('<title>My First Template</title>')

        if (has_title):
            self.assertRegex(string, title_compiled)
            self.assertNotRegex(string, no_title_compiled)
        else:
            self.assertNotRegex(string, title_compiled)
            self.assertRegex(string, no_title_compiled)

    def _content_check_rendering(self, string, has_content=False):

        test_text = re.compile('This is a test.')

        no_value_text = re.compile('<div>The value is </div>')
        value_text = re.compile(
            r'<div>The value is \[\s*\'this\',\s*\'that\',\s*\'the other\',?\s*\]</div>'
        )

        self.assertRegex(string, test_text)

        if (has_content):
            self.assertRegex(string, value_text)
            self.assertNotRegex(string, no_value_text)
        else:
            self.assertRegex(string, no_value_text)
            self.assertNotRegex(string, value_text)

    def check_rendering(self, string, params={}):

        title_bool = 'title' in params
        content_bool = 'content' in params
        self._title_check_rendering(string, title_bool)
        self._content_check_rendering(string, content_bool)

    def check_file_contents(self, new_file, ref_text):

        with open(new_file, 'r') as f:
            rendered_text = f.read()
        self.assertMultiLineEqual(rendered_text.rstrip(), ref_text)

    def test_class_init(self):
        """ TemplateUtil: class initialisation """

        # remove the local config variable: cannot init TTP
        no_conf_err = 'No config file found. Cannot initialise Template Toolkit'
        with modified_environ('KB_DEPLOYMENT_CONFIG'):
            with self.assertRaisesRegex(ValueError, no_conf_err):
                KBaseReport(self.cfg)

        input_tests = self.get_input_set()
        for test_item in input_tests:
            if 'err_field' in test_item and 'config' in test_item['err_field'][0]:
                # init the class directly to check config validation errors
                with self.assertRaisesRegex(TypeError, test_item['regex']):
                    TemplateUtil(test_item['config'])

    def test_template_engine(self):
        """ template engine initialisation """

        tt_config = self.getImpl().config
        tmpl_util = TemplateUtil(tt_config)
        self.assertIsNone(tmpl_util._template)

        # init the template engine
        tmpl_engine = tmpl_util.template_engine()
        self.assertIsInstance(tmpl_engine, Template)

    def test_validate_template_params_errors(self):
        """ test TemplateUtil input validation errors """

        # no scratch dir
        with self.assertRaisesRegex(TypeError, "KBaseReport parameter validation errors:") as cm:
            validate_template_params({'template_file': TEST_DATA['template']}, {
                'this': 'that',
                'the': 'other',
            }, True)
        error_message = str(cm.exception)
        self.assertRegex(error_message, 'scratch.*?required field')

        input_tests = self.get_input_set()
        for test_item in input_tests:
            with self.subTest(test_item['desc']):

                # assume this is input for the saving-to-file method
                with self.assertRaisesRegex(TypeError, test_item['regex']):
                    validate_template_params(
                        test_item['params'], test_item['config'], True)

                with self.assertRaisesRegex(TypeError, test_item['regex']):
                    tmpl_util = TemplateUtil(test_item['config'])
                    tmpl_util.render_template_to_file(test_item['params'])

                # save to direct html -- no output file checks required
                if 'err_field' in test_item and 'params.output_file' in test_item['err_field']:
                    # this should execute without errors
                    validate_template_params(test_item['params'], test_item['config'], False)
                else:
                    with self.assertRaisesRegex(TypeError, test_item['regex']):
                        validate_template_params(
                            test_item['params'], test_item['config'], False)

                    with self.assertRaisesRegex(TypeError, test_item['regex']):
                        tmpl_util = TemplateUtil(test_item['config'])
                        tmpl_util.render_template_to_direct_html({'template': test_item['params']})

    def test_validate_template_params(self):
        """ test TemplateUtil input validation """
        expected = {
            'template_file': TEST_DATA['template'],
            'output_file': TEST_DATA['output_file'],
            'template_data': {},
        }

        # with output file
        self.assertEqual(
            validate_template_params({
                'template_file': TEST_DATA['template'],
                'output_file': TEST_DATA['output_file'],
            }, self.getTmpl().config, True),
            expected
        )

        # JSON input converted to data structure
        expected['template_data'] = TEST_DATA['content']
        self.assertEqual(
            validate_template_params({
                'template_file': TEST_DATA['template'],
                'template_data_json': TEST_DATA['content_json'],
                'output_file': TEST_DATA['output_file'],
            }, self.getTmpl().config, True),
            expected
        )

        # no output file required -- 'output_file' will not be returned in the validated params
        del expected['output_file']
        expected['template_data'] = {}
        self.assertEqual(
            validate_template_params({
                'template_file': TEST_DATA['template'],
                'output_file': TEST_DATA['output_file'],
            }, self.getTmpl().config, False),
            expected
        )

    def test_render_template(self):
        """
        basic rendering test

        function signature:
        _render_template(template_file, template_data={}, template_config={}):

        """
        render_test = TEST_DATA['render_test']
        tmpl_util = self.getTmpl()

        # template not found
        for path in ['/does/not/exist', 'does/not/exist']:
            with self.assertRaisesRegex(TemplateException, 'file error - ' + path + ': not found'):
                tmpl_util._render_template(path)

        for test_item in render_test.keys():
            desc = test_item if test_item is not None else 'None'
            with self.subTest('rendered content: ' + desc):
                if not test_item:
                    # no title or content specified
                    tmpl_str = tmpl_util._render_template(TEST_DATA['template'])
                    self.check_rendering(tmpl_str)
                    self.assertEqual(tmpl_str.rstrip(), render_test[test_item]['abs_path'])

                elif test_item == 'title' or test_item == 'content':
                    tmpl_str = tmpl_util._render_template(
                        TEST_DATA['template'], TEST_DATA[test_item]
                    )
                    self.check_rendering(tmpl_str, {test_item: True})
                    self.assertEqual(tmpl_str.rstrip(), render_test[test_item]['abs_path'])

        # check whether we can use a relative path for a template
        relative_tmpl_str = tmpl_util._render_template(TEST_DATA['template_file'], {})
        self.check_rendering(relative_tmpl_str)
        self.assertEqual(relative_tmpl_str.rstrip(), render_test[None]['rel_path'])

    def test_render_template_to_direct_html(self):
        """ test rendering and saving output to the 'direct_html' param """
        render_test = TEST_DATA['render_test']
        tmpl_util = self.getTmpl()

        # see test_validate_template_params for more validation errors
        with self.assertRaisesRegex(KeyError, 'template.*?required field'):
            tmpl_util.render_template_to_direct_html({
                'template_file': TEST_DATA['template'],
                'template_data_json': TEST_DATA['content_json']
            })

        # template not found
        for path in ['/does/not/exist', 'does/not/exist']:
            with self.assertRaisesRegex(TemplateException, 'file error - ' + path + ': not found'):
                tmpl_util.render_template_to_direct_html({'template': {'template_file': path}})

        for test_item in render_test.keys():
            desc = test_item if test_item is not None else 'None'
            with self.subTest('rendered content: ' + desc):
                test_args = {'template_file': TEST_DATA['template']}

                if test_item:
                    test_args['template_data_json'] = TEST_DATA[test_item + '_json']

                new_params = tmpl_util.render_template_to_direct_html({'template': test_args})

                expected = render_test[test_item]['abs_path']
                direct_html_str = new_params['direct_html']
                self.assertMultiLineEqual(direct_html_str.rstrip(), expected)
                self.assertNotIn('template', new_params)

    def test_render_template_to_file(self):
        """ test rendering and saving to a (scratch) file """

        tmpl_util = self.getTmpl()

        # see test_validate_template_params_errors for more validation errors
        # template not found, absolute and relative paths
        for path in ['/does/not/exist', 'does/not/exist']:
            with self.assertRaisesRegex(TemplateException, 'file error - ' + path + ': not found'):
                tmpl_util.render_template_to_file({
                    'template_file': path,
                    'output_file': TEST_DATA['output_file']
                })

            with self.assertRaisesRegex(TemplateException, 'file error - ' + path + ': not found'):
                tmpl_util.render_template_to_scratch_file({
                    'template_file': path
                })

        # ensure that we can create intervening directories
        output_dir = os.path.join(self.scratch, 'path', 'to', 'new', 'dir')
        self.assertFalse(os.path.isdir(output_dir) and os.path.isfile(output_dir))

        for test_item in TEST_DATA['render_test'].keys():
            desc = test_item if test_item is not None else 'None'

            with self.subTest('rendered content: ' + desc):
                output_file = os.path.join(output_dir, 'temp_file-' + str(uuid4()) + '.txt')
                self.assertFalse(os.path.isfile(output_file))

                test_args = {
                    'template_file': TEST_DATA['template'],
                    'output_file': output_file,
                }

                if test_item:
                    test_args['template_data_json'] = TEST_DATA[test_item + '_json']

                new_file = tmpl_util.render_template_to_file(test_args)
                self.assertEqual(new_file, {'path': output_file})
                self.check_file_contents(
                    new_file['path'], TEST_DATA['render_test'][test_item]['abs_path'])

                # now render these to a temp file instead
                del test_args['output_file']
                tmp_file = tmpl_util.render_template_to_scratch_file(test_args)
                # make sure the file name matches expectations
                self.assertRegex(tmp_file['path'], self.cfg['scratch'] + ".*?.txt$")
                self.check_file_contents(
                    tmp_file['path'], TEST_DATA['render_test'][test_item]['abs_path'])

    def test_impl_render_template_errors(self):
        """ full Impl test errors """
        input_tests = self.get_input_set()
        for test_item in input_tests:
            with self.subTest(test_item['desc']):
                if 'err_field' in test_item:
                    if 'config.template_toolkit' in test_item['err_field'][0]:
                        # this will pass as the TT config gets read (and overwritten) in KBaseReport
                        kbr = KBaseReport(test_item['config'])
                        kbr.render_template({}, test_item['params'])

                    else:
                        with self.assertRaisesRegex(TypeError, test_item['regex']):
                            kbr = KBaseReport(test_item['config'])
                            kbr.render_template({}, test_item['params'])

                        with self.assertRaisesRegex(TypeError, test_item['regex']):
                            kbr = KBaseReport(test_item['config'])
                            kbr.render_templates({}, [test_item['params']])

    def test_impl_render_template(self):
        """ full Impl test: input validation, rendering, saving to file, return """

        for test_item in TEST_DATA['render_test'].keys():
            desc = test_item if test_item is not None else 'none'
            ref_text = TEST_DATA['render_test'][test_item]

            with self.subTest('test content: ' + desc):
                test_args = {
                    'template_file': TEST_DATA['template'],
                    'output_file': os.path.join(self.scratch, 'temp_file-' + str(uuid4()) + '.txt')
                }
                if test_item:
                    test_args['template_data_json'] = TEST_DATA[test_item + '_json']

                impl_output = self.getImpl().render_template({}, test_args)
                self.assertEqual(impl_output, [{'path': test_args['output_file']}])
                self.check_file_contents(impl_output[0]['path'], ref_text['abs_path'])

                # use a relative path instead of the absolute
                test_args['template_file'] = TEST_DATA['template_file']
                test_args['output_file'] = test_args['output_file'] + '-2'
                impl_output_rel_template = self.getImpl().render_template({}, test_args)
                self.assertEqual(impl_output_rel_template, [{'path': test_args['output_file']}])
                self.check_file_contents(impl_output_rel_template[0]['path'], ref_text['rel_path'])

    def test_impl_render_templates_multi_file_errors(self):
        """ full Impl test, multiple templates, errors """

        # name collision in output file names
        args_list = [{
            'template_file': TEST_DATA['template'],
            'output_file': os.path.join(self.scratch, 'temp_file.txt')
        } for _ in range(4)]
        err_str = 'output_file paths must be unique'
        with self.assertRaisesRegex(ValueError, err_str):
            impl_output = self.getImpl().render_templates({}, args_list)

    def test_impl_render_templates(self):
        """
            full Impl test, multiple template rendering:
            input validation, rendering, saving to file, return
        """

        args_list = []
        expected_output = []
        expected_content = {}
        for test_item in TEST_DATA['render_test'].keys():
            ref_text = TEST_DATA['render_test'][test_item]
            test_args = {
                'template_file': TEST_DATA['template'],
                'output_file': os.path.join(self.scratch, 'temp_file-' + str(uuid4()) + '.txt')
            }
            if test_item:
                test_args['template_data_json'] = TEST_DATA[test_item + '_json']

            args_list.append(test_args)
            expected_output.append({
                'path': test_args['output_file'],
            })
            expected_content[test_args['output_file']] = ref_text['abs_path']


        impl_output = self.getImpl().render_templates({}, args_list)

        self.assertEqual(impl_output[0], expected_output)

        for output_file in impl_output[0]:
            self.check_file_contents(output_file['path'], expected_content[output_file['path']])


if __name__ == '__main__':
    unittest.main()
