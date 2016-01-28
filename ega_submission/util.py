import os
import re
import yaml
import click
import xmltodict
import subprocess


def find_workspace_root(cwd=os.getcwd()):
    searching_for = set(['settings', 'file_info', 'study', '.git'])
    last_root    = cwd
    current_root = cwd
    found_path   = None
    while found_path is None and current_root:
        for root, dirs, _ in os.walk(current_root):
            if not searching_for - set(dirs):
                # found the directories, stop
                return root
            # only need to search for the current dir
            break

        # Otherwise, pop up a level, search again
        last_root    = current_root
        current_root = os.path.dirname(last_root)

        # stop if it's already reached os root dir
        if current_root == last_root: break

    return None


def get_settings(wspath):
    config_file = os.path.join(wspath, 'settings', 'config.yaml')
    if not os.path.isfile(config_file):
        return None

    with open(config_file, 'r') as f:
        settings = yaml.load(f)

    return settings


def get_current_dir_type(ctx):
    workplace = ctx.obj['WORKSPACE_PATH']
    current_dir = ctx.obj['CURRENT_DIR']
    if os.path.join(workplace, 'study') == current_dir:
        return 'study'

    pattern = re.compile('%s/([A-Z]+[\-][A-Z]+)/(sample|analysis_variation\..+|analysis_alignment\..+)$' % workplace)
    m = re.match(pattern, current_dir)
    if m and m.group(1) and m.group(2):
        ctx.obj['PROJECT'] = m.group(1)
        if ctx.obj['PROJECT'].startswith('TEST'):
            ctx.obj['IS_TEST_PROJ'] = True
        else:
            ctx.obj['IS_TEST_PROJ'] = False

        if m.group(2) == 'sample' or \
            not set([m.group(2)]) - set(ctx.obj.get('SETTINGS', {}).get('analysis_types')):
            return m.group(2)
        else:
            return None

    return None


def get_template(template_file):
    with open (template_file, 'r') as x: xml_str = x.read()
    return xmltodict.parse(xml_str)


def file_pattern_exist(dirname, pattern):
    files = [f for f in os.listdir(dirname) if os.path.isfile(f)]
    for f in files:
        if re.match(pattern, f): return True

    return False


def submit(ctx, submission_file, metadata_xmls):
    ega_obj_type = 'SUBMISSION'
    files = '-F "%s=@%s" ' % (ega_obj_type, submission_file)

    ega_obj_type = ctx.obj['CURRENT_DIR_TYPE'].upper()
    if ega_obj_type.startswith('ANALYSIS'): ega_obj_type = 'ANALYSIS'

    for f in metadata_xmls:
        files = files + '-F "%s=@%s" ' % (ega_obj_type, f)

    if ctx.obj['IS_TEST']:
        api_endpoint = ctx.obj['SETTINGS']['metadata_endpoint_test'] + ctx.obj['AUTH']
    else:
        api_endpoint = ctx.obj['SETTINGS']['metadata_endpoint_prod'] + ctx.obj['AUTH']

    shell_cmd = 'curl -k %s "%s"' % (files, api_endpoint)

    process = subprocess.Popen(
            shell_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

    out, err = process.communicate()

    if process.returncode:
        # error happened
        click.echo('Unable to download file from cloud.\nError message: {}'.format(err))
        ctx.abort()
    elif 'Login failed' in out:
        click.echo('Login failed!')
        ctx.abort()
    else:
        receipt = xmltodict.unparse(xmltodict.parse(out), pretty=True)
        if 'success="falsed"' in receipt:
            click.echo('Failed, see below for details:\n%s' % receipt)
        else:
            receipt_file = submission_file.replace('.submission-', '.receipt-')
            with open(receipt_file, 'w') as w: w.write(receipt)
            click.echo('Succeeded with response:\n%s' % receipt)

