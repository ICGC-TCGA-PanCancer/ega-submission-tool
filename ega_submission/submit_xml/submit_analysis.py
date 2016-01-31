import os
import re
import json
import click
import calendar
import time
import uuid
import xmltodict
import fnmatch
from ..util import get_template, file_pattern_exist, submit, prepare_submission, get_submitted_items_from_receipt

# not as expected, it turns out EGA submission does not allow more than 1 object per type per submission
# as such, BATCH_SIZE must be set to 1
BATCH_SIZE = 1


def _do_submission(ctx, submission_obj, analyses_to_be_submitted):
    submission_alias = submission_obj['SUBMISSION_SET']['SUBMISSION']['@alias']
    submission_file = os.path.join('analysis', \
        'analysis.%s.submission-%s.xml' % (analyses_to_be_submitted[0], submission_alias))

    with open(submission_file, 'w') as w: w.write(xmltodict.unparse(submission_obj, pretty=True))

    submission_file = os.path.join(os.getcwd(), submission_file)
    metadata_xmls = [os.path.join(os.getcwd(), 'analysis', 'analysis.' + f + '.xml') for f in analyses_to_be_submitted]

    submit(ctx, submission_file, metadata_xmls)


def submit_analysis(ctx, source):
    if not (os.path.isdir(source) and os.path.exists(source)):
        click.echo('Error: specified source is not a directory containing analysis XMLs', err=True)
        ctx.abort()

    # parse all relavent submission receipts to identify items have been submitted before
    submitted_analysis = []
    receipt_file_pattern = 'analysis.*.receipt-test_*.xml' if ctx.obj['IS_TEST'] else 'analysis.*.receipt_*.xml'
    for filename in os.listdir('analysis'):
        if fnmatch.fnmatch(filename, receipt_file_pattern):
            submitted_analysis += \
                get_submitted_items_from_receipt(os.path.join('analysis', filename), 'ANALYSIS', '@alias')

    batch_count = 0
    fc_total = 0
    fc_processed = 0
    pattern = re.compile('^analysis\.([^\.]+)\.xml$')
    analyses_to_be_submitted = []

    for f in os.listdir(source):
        file_with_path = os.path.join(source, f)
        if not os.path.isfile(file_with_path): continue

        m = re.match(pattern, f)
        if m and m.group(1):
            analysis_alias = m.group(1)
        else:
            if ctx.obj['DEBUG']: click.echo('Ingore file does not match naming pattern: %s' % f, err=True)
            continue

        fc_total += 1

        if analysis_alias in submitted_analysis and not ctx.obj.get('FORCE'):
            click.echo('Warning: this xml file "%s" has been submitted to EGA before, will be ignored unless "--force" option is used.' % file_with_path, err=True)
            continue

        analyses_to_be_submitted.append(analysis_alias)

        fc_processed += 1

        if fc_processed % BATCH_SIZE == 0:  # one batch completed
            submission_obj = prepare_submission(ctx, 'analysis', analyses_to_be_submitted)
            _do_submission(ctx, submission_obj, analyses_to_be_submitted)
            batch_count += 1
            analyses_to_be_submitted = []


    if analyses_to_be_submitted:  # there are still some to be submitted
        submission_obj = prepare_submission(ctx, 'analysis',  analyses_to_be_submitted)
        _do_submission(ctx, submission_obj, analyses_to_be_submitted)
        batch_count += 1


    click.echo('Processed %i out of %i input analysis xmls in %i submission(s).' % (fc_processed, fc_total, batch_count))




