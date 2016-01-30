import os
import re
import yaml
import glob
import csv
import click
import xmltodict
import subprocess
import ftplib


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
            ctx.obj['IS_TEST'] = True  # work on TEST project is always a test
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


def ftp_files(path, ctx):
    host = ctx.obj['SETTINGS']['ftp_server']
    _, user, passwd = ctx.obj['AUTH'].split('%20') if len(ctx.obj['AUTH'].split('%20')) == 3 else ('', '', '')

    ftp = ftplib.FTP(host, user, passwd)

    files = []
    try:
        files = ftp.nlst(path)
    except ftplib.error_perm, resp:
        click.echo('Error: unable to connect to FTP server.')
        ctx.abort()

    return files


def load_samples(sample_lookup):
    sample_files = os.path.join('..', 'sample', 'sample.*.tsv')
    for f in glob.glob(sample_files):
        with open(f, 'r') as s:
            reader = csv.DictReader(s, delimiter='\t')
            for sample_info in reader:
                sample_lookup[sample_info['aliquot_id/sample_uuid']] = \
                    sample_info['icgc_sample_id']

def load_file_info(file_info, ctx):
    file_info_dir = '_test_file_info' if ctx.obj['IS_TEST'] else 'file_info'

    staged_file_list = os.path.join(ctx.obj['WORKSPACE_PATH'], file_info_dir, 'staged_files.tsv')
    with open(staged_file_list, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for finfo in reader:
            file_info[finfo['filename']] = {
                'checksum': finfo['checksum'],
                'unencrypted_checksum': finfo['unencrypted_checksum']
            }


def report_missing_file(missed_files, ctx):
    file_info_dir = '_test_file_info' if ctx.obj['IS_TEST'] else 'file_info'

    missed_file_dir = os.path.join(ctx.obj['WORKSPACE_PATH'], file_info_dir, 'missed_files')
    for f in missed_files:
        dirname, filename = f.split('/')
        if not os.path.isdir(os.path.join(missed_file_dir, dirname)):
            os.makedirs(os.path.join(missed_file_dir, dirname))

        open(os.path.join(missed_file_dir, f), 'a').close()


def report_missing_file_info(file_with_path, ctx):
    file_info_dir = '_test_file_info' if ctx.obj['IS_TEST'] else 'file_info'

    info_missing_dir = os.path.join(ctx.obj['WORKSPACE_PATH'], file_info_dir, 'file_info_missing')
    dirname, filename = file_with_path.split('/')
    if not os.path.isdir(os.path.join(info_missing_dir, dirname)):
        os.makedirs(os.path.join(info_missing_dir, dirname))

    open(os.path.join(info_missing_dir, file_with_path), 'a').close()


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
        failed = False
        try:
            receipt_obj = xmltodict.parse(out)
            receipt = xmltodict.unparse(receipt_obj, pretty=True)
            if receipt_obj['RECEIPT']['@success'].lower() == 'true':
                receipt_file = submission_file.replace('.submission-', '.receipt-')
                with open(receipt_file, 'w') as w: w.write(receipt)
                click.echo('Succeeded with response:\n%s' % receipt)
            else:
                click.echo('Failed, see below for details:\n%s' % receipt)
                failed = True  # can't call abort() here, must flag it instead
        except Exception, e:  # if the output is not an XML, it's failed
            click.echo('Failed, unknown response type, see below for details:\n%s\n%s' % (out, e))
            ctx.abort()

        if failed: ctx.abort()
