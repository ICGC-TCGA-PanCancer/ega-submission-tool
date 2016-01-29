import os
from ..util import ftp_files


def build_alignment_analysis(analysis_obj, analysis_info, gnos_analysis_id, sample_lookup, ctx):
    # we may not need to use analysis_type (ctx.obj['CURRENT_DIR_TYPE']), WGS and RNA-Seq alignment
    # may be the same code

    analysis_obj['ANALYSIS_SET']['ANALYSIS']['@alias'] = gnos_analysis_id
    analysis_obj['ANALYSIS_SET']['ANALYSIS']['@center_name'] = analysis_info['@center_name']
    analysis_obj['ANALYSIS_SET']['ANALYSIS']['@broker_name'] = 'EGA'  # hardcode
    analysis_obj['ANALYSIS_SET']['ANALYSIS']['@analysis_center'] = analysis_info['@analysis_center']
    analysis_obj['ANALYSIS_SET']['ANALYSIS']['@analysis_date'] = analysis_info['@analysis_date']
    analysis_obj['ANALYSIS_SET']['ANALYSIS']['TITLE'] = analysis_info['TITLE']
    analysis_obj['ANALYSIS_SET']['ANALYSIS']['DESCRIPTION'] = analysis_info['DESCRIPTION']
    analysis_obj['ANALYSIS_SET']['ANALYSIS']['STUDY_REF']['@refname'] = 'PCAWG'  # hardcode this here
    analysis_obj['ANALYSIS_SET']['ANALYSIS']['STUDY_REF']['@refcenter'] = ctx.obj['SETTINGS']['centre_name']

    sample_uuid = analysis_info['TARGETS']['TARGET']['@refname']
    analysis_obj['ANALYSIS_SET']['ANALYSIS']['SAMPLE_REF']['@label'] \
        = sample_uuid
    analysis_obj['ANALYSIS_SET']['ANALYSIS']['SAMPLE_REF']['@refname'] \
        = sample_lookup.get(sample_uuid)
    analysis_obj['ANALYSIS_SET']['ANALYSIS']['SAMPLE_REF']['@refcenter'] \
        = analysis_info['TARGETS']['TARGET']['@refcenter']

    analysis_obj['ANALYSIS_SET']['ANALYSIS']['ANALYSIS_TYPE']['REFERENCE_ALIGNMENT']['SEQUENCE'] \
        = analysis_info['ANALYSIS_TYPE']['REFERENCE_ALIGNMENT']['SEQ_LABELS']['SEQUENCE']

    for s in analysis_info['ANALYSIS_TYPE']['REFERENCE_ALIGNMENT']['SEQ_LABELS']['SEQUENCE']:
        s['@label'] = s['@seq_label']
        del s['@data_block_name']
        del s['@seq_label']

    analysis_obj['ANALYSIS_SET']['ANALYSIS']['ANALYSIS_ATTRIBUTES']['ANALYSIS_ATTRIBUTE'] \
        = analysis_info['ANALYSIS_ATTRIBUTES']['ANALYSIS_ATTRIBUTE']

    # TODO: get file info (checksums)

    files = {
        'readme_file': {
            #'filename': os.path.join(gnos_analysis_id, 'analysis.%s.GNOS.xml' % gnos_analysis_id),
            'filename': os.path.join(gnos_analysis_id, 'test.txt'),
            'checksum': 'ae4b28479dc6652ba00a73ec76c8be95',
            'unencrypted_checksum': 'ae4b28479dc6652ba00a73ec76c8be95'  # TODO
        }
    }
    for f in analysis_info['DATA_BLOCK']['FILES']['FILE']:
        files[f['@filetype']] = {
            'filename': os.path.join(gnos_analysis_id, f['@filename']),
            'checksum': f['@checksum'],
            'unencrypted_checksum': 'ae4b28479dc6652ba00a73ec76c8be95'  # TODO
        }

    # get list of files on the FTP server under 'gnos_analysis_id' folder
    staged_files = ftp_files(gnos_analysis_id, ctx)

    missed_files = []
    for f in analysis_obj['ANALYSIS_SET']['ANALYSIS']['FILES']['FILE']:
        ftype = f['@filetype']
        f['@filename'] = files[ftype]['filename']
        f['@checksum'] = files[ftype]['checksum']
        f['@unencrypted_checksum'] = files[ftype]['unencrypted_checksum']

        if not f['@filename'] + '.gpg' in staged_files:
            missed_files.append(f['@filename'] + '.gpg')

    if missed_files: return missed_files

    return []


def build_variation_analysis(analysis_obj, analysis_info, gnos_analysis_id, sample_lookup, ctx):
    pass

