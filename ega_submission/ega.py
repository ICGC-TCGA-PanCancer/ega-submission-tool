import os
import click
import util
from prepare_xml import *
from submit_xml import *


def initialize_workspace(ctx):
    ctx.obj['CURRENT_DIR'] = os.getcwd()
    ctx.obj['IS_TEST_PROJ'] = None
    ctx.obj['WORKSPACE_PATH'] = util.find_workspace_root()
    if not ctx.obj['WORKSPACE_PATH']:
        click.echo('Error: not in an EGA submission workspace!')
        ctx.abort()

    # for debugging only
    #click.echo('Workspace: %s' % ctx.obj['WORKSPACE_PATH'])

    # read the settings
    ctx.obj['SETTINGS'] = util.get_settings(ctx.obj['WORKSPACE_PATH'])
    if not ctx.obj['SETTINGS']:
        click.echo('Error: unable to read config file, or config file invalid!')
        ctx.abort()

    # figure out the current dir type, e.g., study, sample or analysis
    ctx.obj['CURRENT_DIR_TYPE'] = util.get_current_dir_type(ctx)
    if not ctx.obj['CURRENT_DIR_TYPE']:
        click.echo('Error: the current working directory does not associate with any known EGA object type')
        ctx.abort()

    # for debugging only
    #click.echo(ctx.obj)


def prepare(ctx, ega_type, source):
    #click.echo(ctx.obj)
    if ega_type == 'study':
        prepare_study(ctx, source)
    elif ega_type == 'sample':
        prepare_sample(ctx, source)
    elif ega_type == 'analysis':
        prepare_analysis(ctx, source)
    elif ega_type == 'dataset':
        prepare_dataset(ctx, source)
    else:
        click.echo('Unknown object type: %s' % ega_type)
        ctx.abort()

    click.echo( 'Prepared %s' % ega_type )


def submit(ctx, ega_type, source):
    #click.echo(ctx.obj)
    if ega_type == 'study':
        submit_study(ctx, source)
    elif ega_type == 'sample':
        submit_sample(ctx, source)
    elif ega_type == 'analysis':
        submit_analysis(ctx, source)
    elif ega_type == 'dataset':
        submit_dataset(ctx, source)
    else:
        click.echo('Unknown object type: %s' % ega_type)
        ctx.abort()

    click.echo( 'Submitted %s' % ega_type )

