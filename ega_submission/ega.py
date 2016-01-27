import click
import util


def initialize_workspace(ctx):
    ctx.obj['WORKSPLACE_PATH'] = util.find_workspace_root()
    if not ctx.obj['WORKSPLACE_PATH']:
        click.echo('Error: not in an EGA submission workspace!')
        ctx.abort()

    click.echo('Workspace: %s' % ctx.obj['WORKSPLACE_PATH'])

    # read the settings

    # figure out the current dir, e.g., study, sample or analysis

    # figure out the current project, e.g., CLLE-ES

    # figure out whether its a test project


def prepare_study(ctx):
    click.echo('Sorry, not implemented yet.')
    ctx.abort()


def prepare_sample(ctx):
    click.echo('Sorry, not implemented yet.')
    ctx.abort()


def prepare_analysis(ctx):
    click.echo('Sorry, not implemented yet.')
    ctx.abort()


def prepare_dataset(ctx):
    click.echo('Sorry, not implemented yet.')
    ctx.abort()


def submit_study(ctx):
    click.echo('Sorry, not implemented yet.')
    ctx.abort()


def submit_sample(ctx):
    click.echo('Sorry, not implemented yet.')
    ctx.abort()


def submit_analysis(ctx):
    click.echo('Sorry, not implemented yet.')
    ctx.abort()


def submit_dataset(ctx):
    click.echo('Sorry, not implemented yet.')
    ctx.abort()


def prepare(ctx, ega_type):
    #click.echo(repr(ctx.obj))

    if ega_type == 'study':
        prepare_study(ctx)
    elif ega_type == 'sample':
        prepare_sample(ctx)
    elif ega_type == 'analysis':
        prepare_analysis(ctx)
    elif ega_type == 'dataset':
        prepare_dataset(ctx)
    else:
        click.echo('Unknown object type: %s' % ega_type)
        ctx.abort()

    click.echo( "Prepared %s" % ega_type )


def submit(ctx, ega_type):
    #click.echo(repr(ctx.obj))

    if ega_type == 'study':
        submit_study(ctx)
    elif ega_type == 'sample':
        submit_sample(ctx)
    elif ega_type == 'analysis':
        submit_analysis(ctx)
    elif ega_type == 'dataset':
        submit_dataset(ctx)
    else:
        click.echo('Unknown object type: %s' % ega_type)
        ctx.abort()

    click.echo( "Submitted %s" % ega_type )

