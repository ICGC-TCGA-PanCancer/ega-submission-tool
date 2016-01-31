import os
import fnmatch
import click
import copy
import xmltodict
from ..util import get_submitted_items_from_receipt, get_template

import json

def prepare_dataset(ctx, source):
    source = source.rstrip('/')
    if not source == 'analysis':
        click.echo('Error: the source must be "analysis" for preparing dataset.', err=True)
        ctx.abort()

    if not (os.path.isdir(source) and os.path.exists(source)):
        click.echo('Error: specified source is not a directory containing submitted analysis XMLs', err=True)
        ctx.abort()

    # parse all relavent submission receipts to identify items (accession) have been submitted before
    submitted_analysis = []
    receipt_file_pattern = 'analysis.*.receipt-test_*.xml' if ctx.obj['IS_TEST'] else 'analysis.*.receipt_*.xml'
    for filename in os.listdir(source):
        if fnmatch.fnmatch(filename, receipt_file_pattern):
            submitted_analysis += \
                get_submitted_items_from_receipt(os.path.join('analysis', filename), 'ANALYSIS', '@accession')

    # read dataset template xml file
    template_file = os.path.join(ctx.obj['WORKSPACE_PATH'], 'settings', 'dataset.template.xml')
    dataset_obj = get_template(template_file)

    dataset_name = '%s_%s' % (ctx.obj['PROJECT'], ctx.obj['CURRENT_DIR_TYPE'].split('.')[1])

    dataset_obj['DATASETS']['DATASET']['TITLE'] = \
        dataset_obj['DATASETS']['DATASET']['TITLE'] % dataset_name
    dataset_obj['DATASETS']['DATASET']['DESCRIPTION'] = \
        ctx.obj['SETTINGS']['analysis_types'][ctx.obj['CURRENT_DIR_TYPE']].rstrip() % ctx.obj['PROJECT']
    dataset_obj['DATASETS']['DATASET']['@alias'] = dataset_name

    analysis_refs = dataset_obj['DATASETS']['DATASET']['ANALYSIS_REF']
    del analysis_refs[0]
    analysis_ref = analysis_refs.pop(0)

    for analysis_acc in submitted_analysis:
        analysis_ref['@accession'] = analysis_acc
        analysis_refs.append(copy.deepcopy(analysis_ref))

    #click.echo(json.dumps(dataset_obj, indent=2))
    #click.echo(xmltodict.unparse(dataset_obj, pretty=True))

    out_file = 'dataset.%s.xml' % dataset_name
    if os.path.isfile(out_file) and not ctx.obj.get('FORCE'):
        click.echo('Error: this dataset XML file has been generated before, will not overwrite without "--force" option.', err=True)
        ctx.abort()

    with open(out_file, 'w') as w: w.write(xmltodict.unparse(dataset_obj, pretty=True))

