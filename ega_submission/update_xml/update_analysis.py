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


def _do_submission(ctx, submission_obj, analyses_to_be_updated):
    submission_alias = submission_obj['SUBMISSION_SET']['SUBMISSION']['@alias']
    submission_file = os.path.join('analysis', \
        'analysis.%s.submission-%s.xml' % (analyses_to_be_updated[0], submission_alias))

    with open(submission_file, 'w') as w: w.write(xmltodict.unparse(submission_obj, pretty=True))

    submission_file = os.path.join(os.getcwd(), submission_file)
    metadata_xmls = [os.path.join(os.getcwd(), 'analysis', 'analysis.' + f + '.xml') for f in analyses_to_be_updated]

    if not submit(ctx, 'ANALYSIS', submission_file, metadata_xmls, 'MODIFY'):
        click.echo('Submission failed, see above for more details.\n\n', err=True)
        return False
    else:
        return True


def update_analysis(ctx, source):
    if not (os.path.isdir(source) and os.path.exists(source)):
        click.echo('Error: specified source is not a directory containing analysis XMLs', err=True)
        ctx.abort()

    # parse all relavent submission receipts to identify items have been submitted before
    submitted_analysis = {}
    receipt_file_pattern = 'analysis.*.receipt-test_*.xml' if ctx.obj['IS_TEST'] else 'analysis.*.receipt-*.xml'
    for filename in os.listdir('analysis'):
        if not ctx.obj['IS_TEST'] and 'receipt-test_' in filename: continue

        if fnmatch.fnmatch(filename, receipt_file_pattern):
            submitted_analysis.update(get_submitted_items_from_receipt(os.path.join(os.getcwd(), 'analysis', filename), 'ANALYSIS', ''))
                

    batch_count = 0
    fc_total = 0
    fc_processed = 0
    success_count = 0
    pattern = re.compile('^analysis\.([^\.]+)\.xml$')
    analyses_to_be_updated = []

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

        if not analysis_alias in submitted_analysis.keys():
            click.echo('Warning: this xml file "%s" has not been submitted to EGA before, can not be updated.' % file_with_path, err=True)
            continue

        analyses_to_be_updated.append(analysis_alias)
        update_original_xml_with_ega_accession('analysis', file_with_path, submitted_analysis)

        fc_processed += 1

        if fc_processed % BATCH_SIZE == 0:  # one batch completed
            submission_obj = prepare_submission(ctx, 'analysis', analyses_to_be_updated, 'MODIFY')
            if _do_submission(ctx, submission_obj, analyses_to_be_updated): success_count += 1
            batch_count += 1
            analyses_to_be_updated = []


    if analyses_to_be_updated:  # there are still some to be submitted
        submission_obj = prepare_submission(ctx, 'analysis',  analyses_to_be_updated, 'MODIFY')
        if _do_submission(ctx, submission_obj, analyses_to_be_updated): success_count += 1
        batch_count += 1


    click.echo('Processed %i out of %i input analysis xmls in %i submission(s), %i MODIFY submission(s) succeeded.' \
        % (fc_processed, fc_total, batch_count, success_count), err=True)  # output to stderr, not really err here
