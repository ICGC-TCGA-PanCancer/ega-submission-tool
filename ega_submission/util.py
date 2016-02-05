import os
import re
import yaml
import glob
import csv
import click
import copy
import xmltodict
import subprocess
import ftplib
import calendar
import time
import uuid


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
        if not ctx.obj['SETTINGS']['projects'].get(ctx.obj['PROJECT']):
            click.echo('Error: unknown project - %s' % ctx.obj['PROJECT'])
            ctx.abort()

        if ctx.obj['PROJECT'].startswith('TEST'):
            ctx.obj['IS_TEST_PROJ'] = True
            ctx.obj['IS_TEST'] = True  # work on TEST project is always a test
        else:
            ctx.obj['IS_TEST_PROJ'] = False

        if m.group(2) == 'sample' or \
            not set([m.group(2)]) - set(ctx.obj.get('SETTINGS', {}).get('analysis_types').keys()):
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


def prepare_submission(ctx, ega_type, objects_to_be_submitted):
    # read submission template xml file
    template_file = os.path.join(ctx.obj['WORKSPACE_PATH'], 'settings', 'submission.template.xml')
    submission_obj = get_template(template_file)

    epoch_time = str(int(calendar.timegm(time.gmtime())))
    uuid_str = str(uuid.uuid4())
    alias_parts = [epoch_time, uuid_str]
    if ctx.obj['IS_TEST']: alias_parts.insert(0, 'test')
    submission_alias = '_'.join(alias_parts)

    try:
        submission_obj['SUBMISSION_SET']['SUBMISSION']['@alias'] = submission_alias
        actions = submission_obj['SUBMISSION_SET']['SUBMISSION']['ACTIONS']['ACTION']
        action = actions.pop(0)  # remove the first placeholder action
        source_file_pattern = re.compile('^' + ega_type + '\.' + '.+\.xml$')
        for source in objects_to_be_submitted:
            action['ADD']['@source'] = source if re.match(source_file_pattern, source) else '.'.join([ega_type, source, 'xml'])
            action['ADD']['@schema'] = ega_type
            actions.insert(0, copy.deepcopy(action))  # add action back in the first place

    except Exception, e:
        click.echo('Error: %s' % str(e), err=True)
        ctx.abort()

    return submission_obj


def ftp_files(path, ctx):
    host = ctx.obj['SETTINGS']['ftp_server']
    _, user, passwd = ctx.obj['AUTH'].split('%20') if len(ctx.obj['AUTH'].split('%20')) == 3 else ('', '', '')

    ftp = ftplib.FTP(host, user, passwd)

    files = []
    try:
        files = ftp.nlst(path)
    except ftplib.error_perm, resp:
        click.echo('Error: unable to connect to FTP server.', err=True)
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

    staged_file_list = [ os.path.join(ctx.obj['WORKSPACE_PATH'], file_info_dir, 'file_info.tsv') ]

    staged_file_list += glob.glob(os.path.join(ctx.obj['WORKSPACE_PATH'], \
        file_info_dir, 'GNOS_xml_file_info', '*.tsv'))

    for fs in staged_file_list:
        print fs
        with open(fs, 'r') as f:
            reader = csv.DictReader(f, delimiter='\t')
            for finfo in reader:
                file_info[finfo['filename']] = {
                    'checksum': finfo['checksum'],
                    'unencrypted_checksum': finfo['unencrypted_checksum']
                }


def report_missing_file(missed_files, ctx):
    file_info_dir = '_test_file_info' if ctx.obj['IS_TEST'] else 'file_info'

    missed_file_dir = os.path.join(ctx.obj['WORKSPACE_PATH'], file_info_dir, 'files_missed_on_ftp_server')
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


def update_original_xml_with_ega_accession(ega_type, metadata_xmls, receipt_file):
    submitted_items = get_submitted_items_from_receipt(receipt_file, ega_type, '')

    for xml in metadata_xmls:
        with open(xml, 'r') as x: xml_str = x.read()
        metadata_obj = xmltodict.parse(xml_str)
        root_el = metadata_obj.keys()[0]  # XML must have only one root
        if not isinstance(metadata_obj[root_el][ega_type], list):
            metadata_obj[root_el][ega_type] = [ metadata_obj[root_el][ega_type] ]

        for item in metadata_obj[root_el][ega_type]:
            item['@accession'] = submitted_items.get(item['@alias'])

        # write back to the same file with accession added
        with open(xml, 'w') as x: x.write(xmltodict.unparse(metadata_obj, pretty=True))


def submit(ctx, ega_type, submission_file, metadata_xmls):
    ega_obj_type = 'SUBMISSION'
    files = '-F "%s=@%s" ' % (ega_obj_type, submission_file)

    ega_obj_type = ega_type.upper()

    for f in metadata_xmls:
        files = files + '-F "%s=@%s" ' % (ega_obj_type, f)

    if ctx.obj['IS_TEST']:
        api_endpoint = ctx.obj['SETTINGS']['metadata_endpoint_test'] + ctx.obj['AUTH']
    else:
        api_endpoint = ctx.obj['SETTINGS']['metadata_endpoint_prod'] + ctx.obj['AUTH']

    shell_cmd = 'curl -k %s "%s"' % (files, api_endpoint)
    #click.echo(shell_cmd)  # debug
    process = subprocess.Popen(
            shell_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

    out, err = process.communicate()

    if process.returncode:
        # error happened
        click.echo('Unable to communicate with FTP server, Error message: %s' % err, err=True)
        ctx.abort()
    elif 'Login failed' in out:
        click.echo('Login failed!', err=True)
        ctx.abort()
    else:
        failed = False
        try:
            receipt_obj = xmltodict.parse(out)
            receipt = xmltodict.unparse(receipt_obj, pretty=True)
            if receipt_obj['RECEIPT']['@success'].lower() == 'true':
                receipt_file = submission_file.replace('.submission-', '.receipt-')
                with open(receipt_file, 'w') as w: w.write(receipt)

                if not ctx.obj['IS_TEST']:
                    update_original_xml_with_ega_accession(ega_obj_type, metadata_xmls, receipt_file)

                click.echo('Succeeded with response:\n%s\n\n' % receipt, err=True)  # not error, just to output this to stderr
            else:
                click.echo('Failed, see below for details:\n%s' % receipt, err=True)
                failed = True  # can't call abort() here, must flag it instead
        except Exception, e:  # if the output is not an XML, it's failed
            click.echo('Failed, unknown response type, see below for details:\n%s\n%s' % (out, e), err=True)
            ctx.abort()

        if failed:
            return False
        else:
            return True


def get_submitted_items_from_receipt(filename, ega_type, identifier):
    ega_type = ega_type.upper()
    identifier = identifier.lower()
    if not ega_type in ('SUBMISSION', 'STUDY', 'SAMPLE', 'ANALYSIS', 'DATASET'):
        click.echo('Warning: unknown EGA type be extracted from EGA submisson receipt - %s' % ega_type, err=True)
        return []
    elif not identifier in ('@accession', '@alias', ''):  # empty value means the client wants a dict back
        click.echo('Warning: unknown EGA type be extracted from EGA submisson receipt - %s' % ega_type, err=True)
        return []

    with open (filename, 'r') as x: xml_str = x.read()
    receipt_obj = xmltodict.parse(xml_str)
    items = receipt_obj.get('RECEIPT', {}).get(ega_type)
    if items:
        if not isinstance(items, list): items = [ copy.deepcopy(items) ]

        if identifier == '':
            return {i.get('@alias'): i.get('@accession') for i in items}
        else:
            return [i.get(identifier) for i in items]

    return({} if identifier == '' else [])
