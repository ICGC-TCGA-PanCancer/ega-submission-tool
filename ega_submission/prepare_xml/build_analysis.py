import os
import click
from ..util import ftp_files, report_missing_file, report_missing_file_info, get_md5sum_from_ftp_server


def build_alignment_analysis(analysis_obj, analysis_info, gnos_analysis_id, sample_lookup, file_info, ctx):
    # we may not need to use analysis_type (ctx.obj['CURRENT_DIR_TYPE']), WGS and RNA-Seq alignment
    # may be the same code
    analysis_obj['ANALYSIS_SET']['ANALYSIS']['@alias'] = gnos_analysis_id
    analysis_obj['ANALYSIS_SET']['ANALYSIS']['@center_name'] = analysis_info.get('@center_name', '')
    analysis_obj['ANALYSIS_SET']['ANALYSIS']['@broker_name'] = 'EGA'  # hardcode
    analysis_obj['ANALYSIS_SET']['ANALYSIS']['@analysis_center'] = analysis_info.get('@analysis_center', '')
    analysis_obj['ANALYSIS_SET']['ANALYSIS']['@analysis_date'] = analysis_info.get('@analysis_date', '')
    analysis_obj['ANALYSIS_SET']['ANALYSIS']['TITLE'] = analysis_info.get('TITLE', '')
    analysis_obj['ANALYSIS_SET']['ANALYSIS']['DESCRIPTION'] = analysis_info.get('DESCRIPTION', '')
    analysis_obj['ANALYSIS_SET']['ANALYSIS']['STUDY_REF']['@refname'] = 'PCAWG'  # hardcode this here
    analysis_obj['ANALYSIS_SET']['ANALYSIS']['STUDY_REF']['@refcenter'] = ctx.obj['SETTINGS']['centre_name']

    sample_uuid = analysis_info['TARGETS']['TARGET']['@refname']
    analysis_obj['ANALYSIS_SET']['ANALYSIS']['SAMPLE_REF']['@label'] \
        = sample_uuid

    sample_refname = sample_lookup.get(sample_uuid)
    if not sample_refname:
        click.echo('Warning: missing sample ID lookup for %s in GNOS object %s' % (sample_uuid, gnos_analysis_id), err=True)
        return False

    analysis_obj['ANALYSIS_SET']['ANALYSIS']['SAMPLE_REF']['@refname'] = sample_refname
    analysis_obj['ANALYSIS_SET']['ANALYSIS']['SAMPLE_REF']['@refcenter'] = ctx.obj['SETTINGS']['centre_name']  # must be the same

    analysis_obj['ANALYSIS_SET']['ANALYSIS']['ANALYSIS_TYPE']['REFERENCE_ALIGNMENT']['SEQUENCE'] \
        = analysis_info['ANALYSIS_TYPE']['REFERENCE_ALIGNMENT']['SEQ_LABELS']['SEQUENCE']

    for s in analysis_info['ANALYSIS_TYPE']['REFERENCE_ALIGNMENT']['SEQ_LABELS']['SEQUENCE']:
        s['@label'] = s['@seq_label']
        del s['@data_block_name']
        del s['@seq_label']

    analysis_obj['ANALYSIS_SET']['ANALYSIS']['ANALYSIS_ATTRIBUTES']['ANALYSIS_ATTRIBUTE'] \
        = analysis_info['ANALYSIS_ATTRIBUTES']['ANALYSIS_ATTRIBUTE']

    filename = os.path.join(gnos_analysis_id, 'analysis.%s.GNOS.xml.gz' % gnos_analysis_id)  # the gnos xml as readme
    if not file_info.get(filename + '.gpg') \
        or not file_info[filename + '.gpg']['checksum'] \
        or not file_info[filename + '.gpg']['unencrypted_checksum']:

            # now get md5sum from the FTP server
            get_md5sum_from_ftp_server(filename, file_info, ctx)

            if not file_info.get(filename + '.gpg') \
                or not file_info[filename + '.gpg']['checksum'] \
                or not file_info[filename + '.gpg']['unencrypted_checksum']:

                click.echo('Warning: missing file info (checksum or unencrypted_checksum, or both) for: %s' % filename, err=True)
                report_missing_file_info(filename + '.gpg', ctx)
                return False

    files = {
        'readme_file': {
            'filename': filename,
            'checksum': file_info[filename + '.gpg']['checksum'],
            'unencrypted_checksum': file_info[filename + '.gpg']['unencrypted_checksum']
        }
    }

    # special handel for xmls which only contain one file information in the DATA_BLOCK
    if isinstance(analysis_info['DATA_BLOCK']['FILES']['FILE'], dict):
        file_list = [analysis_info['DATA_BLOCK']['FILES']['FILE']]  
    elif isinstance(analysis_info['DATA_BLOCK']['FILES']['FILE'], list):
        file_list = analysis_info['DATA_BLOCK']['FILES']['FILE'] 
    else:
        click.echo('Warning: DATA_BLOCK in GNOS xml was likely incorrectly populated!')
        return False

    for f in file_list:
        filename = os.path.join(gnos_analysis_id, f['@filename'])

        if not file_info.get(filename + '.gpg') \
            or not file_info[filename + '.gpg']['checksum'] \
            or not file_info[filename + '.gpg']['unencrypted_checksum']:

            # now get md5sum from the FTP server
            get_md5sum_from_ftp_server(filename, file_info, ctx)

            if not file_info.get(filename + '.gpg') \
                or not file_info[filename + '.gpg']['checksum'] \
                or not file_info[filename + '.gpg']['unencrypted_checksum']:

                click.echo('Warning: missing file info (checksum or unencrypted_checksum, or both) for: %s' % filename, err=True)
                report_missing_file_info(filename + '.gpg', ctx)
                return False

        if not file_info[filename + '.gpg']['unencrypted_checksum'] == f['@checksum']:
            click.echo('Warning: md5sum for unencrypted file in file_info.tsv is different from what is in GNOS xml for: %s' % filename, err=True)
            return False

        files[f['@filetype']] = {
            'filename': filename,
            'checksum': file_info[filename + '.gpg']['checksum'],
            'unencrypted_checksum': file_info[filename + '.gpg']['unencrypted_checksum']
        }
        if filename.endswith('bam'): bam_filename = filename

    # special handel for many RNA-Seq xmls which do not contain bai information in the DATA_BLOCK
    if not files.get('bai'):
        filename = bam_filename+'.bai'
        if not file_info.get(filename + '.gpg') \
            or not file_info[filename + '.gpg']['checksum'] \
            or not file_info[filename + '.gpg']['unencrypted_checksum']:

                # now get md5sum from the FTP server
                get_md5sum_from_ftp_server(filename, file_info, ctx)

                if not file_info.get(filename + '.gpg') \
                    or not file_info[filename + '.gpg']['checksum'] \
                    or not file_info[filename + '.gpg']['unencrypted_checksum']:

                    click.echo('Warning: missing file info (checksum or unencrypted_checksum, or both) for: %s' % filename, err=True)
                    report_missing_file_info(filename + '.gpg', ctx)
                    return False

        files['bai'] = {
                'filename': filename,
                'checksum': file_info[filename + '.gpg']['checksum'],
                'unencrypted_checksum': file_info[filename + '.gpg']['unencrypted_checksum']
        }        

    # get list of files on the FTP server under 'gnos_analysis_id' folder
    staged_files = ftp_files(gnos_analysis_id, ctx)

    missed_files = []
    for f in analysis_obj['ANALYSIS_SET']['ANALYSIS']['FILES']['FILE']:
        ftype = f['@filetype']
        f['@filename'] = files[ftype]['filename']
        f['@checksum'] = files[ftype]['checksum']
        f['@unencrypted_checksum'] = files[ftype]['unencrypted_checksum']

        if not f['@filename'] + '.gpg' in staged_files: missed_files.append(f['@filename'] + '.gpg')

    if missed_files:
        click.echo('Warning: missing files on FTP for GNOS xml: %s' % gnos_analysis_id, err=True)
        report_missing_file(missed_files, ctx)
        return False

    return True


def build_variation_analysis(analysis_obj, analysis_info, gnos_analysis_id, sample_lookup, file_info, ctx):
    pass

