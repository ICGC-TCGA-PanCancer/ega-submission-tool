import os
import re
import click
import xmltodict
import json
import copy
from build_analysis import build_alignment_analysis, build_variation_analysis
from ..util import get_template, load_samples, load_file_info, report_missing_file


def prepare_analysis(ctx, source):
    source = source.rstrip('/')
    regex = '^GNOS_xml$'
    if not re.match(re.compile(regex), source):
        click.echo('Error: specified source file does not match naming convention: %s' % regex)
        ctx.abort()

    if not os.path.isdir(source):
        click.echo('Error: specified source file does not exist.')
        ctx.abort()

    # read template xml file
    if ctx.obj['CURRENT_DIR_TYPE'].startswith('analysis_alignment.'):
        template_file = os.path.join(ctx.obj['WORKSPACE_PATH'], 'settings', 'analysis_alignment.template.xml')
    elif ctx.obj['CURRENT_DIR_TYPE'].startswith('analysis_variation.'):
        template_file = os.path.join(ctx.obj['WORKSPACE_PATH'], 'settings', 'analysis_variation.template.xml')
    else:
        click.echo('Error: no template file found for this analysis type - %s' % ctx.obj['CURRENT_DIR_TYPE'])
        ctx.abort()

    analysis_template_obj = get_template(template_file)

    sample_lookup = {}
    file_info = {}

    # scan for GNOS analysis in the GNOS_xml folder
    fc_total = 0
    fc_processed = 0
    for f in os.listdir(source):
        file_with_path = os.path.join(source,f)
        if not os.path.isfile(file_with_path): continue

        # file name convention
        pattern = re.compile('^analysis\.([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})\.GNOS\.xml$')
        m = re.match(pattern, f)
        if m and m.group(1):
            gnos_analysis_id = m.group(1)
        else:
            if ctx.obj['DEBUG']: click.echo('Ingore file does not match naming pattern: %s', f)
            continue

        fc_total += 1

        if os.path.isfile(file_with_path + '.processed') and not ctx.obj.get('FORCE'):
            click.echo('Warning: this source file "%s" has been converted to EGA XML before, will be ignored unless "--force" option is used.' % file_with_path)
            continue

        with open (file_with_path, 'r') as x: xml_str = x.read()
        analysis_info = xmltodict.parse(xml_str)['ResultSet']['Result']['analysis_xml']['ANALYSIS_SET']['ANALYSIS']

        analysis_obj = copy.deepcopy(analysis_template_obj)

        # we wait until the last moment to do this - lazy load
        if not sample_lookup: load_samples(sample_lookup)
        if not sample_lookup:
            click.echo('Error: no sample info available.')
            ctx.abort()

        if not file_info: load_file_info(file_info, ctx)
        if not file_info:
            click.echo('Error: no staged file info (md5sum etc) available.')
            ctx.abort()

        if ctx.obj['CURRENT_DIR_TYPE'].startswith('analysis_alignment.'):
            rev = build_alignment_analysis(analysis_obj, analysis_info, gnos_analysis_id, sample_lookup, file_info, ctx)
        elif ctx.obj['CURRENT_DIR_TYPE'].startswith('analysis_variation.'):
            rev = build_variation_analysis(analysis_obj, analysis_info, gnos_analysis_id, sample_lookup, file_info, ctx)

        #click.echo(json.dumps(analysis_obj, indent=2))
        #click.echo(xmltodict.unparse(analysis_obj, pretty=True))
        if not rev: continue

        # write the flag file to mark its been processed
        with open(file_with_path + '.processed', 'w') as w: w.write('')

        fc_processed += 1
        out_file = os.path.join('analysis', re.sub(r'\.GNOS\.xml$', '.xml', f))
        with open(out_file, 'w') as w: w.write(xmltodict.unparse(analysis_obj, pretty=True))


    click.echo('Processed %i out of %i input GNOS xmls' % (fc_processed, fc_total))
