import click
import ega


@click.group()
@click.option('--auth', envvar='EGASUB_AUTH')
@click.option('--debug/--no-debug', default=False, envvar='EGASUB_DEBUG')
@click.pass_context
def main(ctx, auth, debug):
    # initializing ctx.obj
    ctx.obj = {}
    ctx.obj['AUTH'] = auth
    ctx.obj['DEBUG'] = debug
    if ctx.obj['DEBUG']: click.echo('Debug is on.')

    ega.initialize_workspace(ctx)


@main.command()
@click.argument('ega_type', nargs=1)
@click.pass_context
def prepare(ctx, ega_type):
    click.echo('This is to prepare for %s.' % ega_type)

    ega.prepare(ctx, ega_type)


@main.command()
@click.pass_context
def validate(ctx):

    click.echo('This has not been implemented yet.')


@main.command()
@click.argument('ega_type', nargs=1)
@click.pass_context
def submit(ctx, ega_type):
    click.echo('This is to submit %s.' % ega_type)

    ega.submit(ctx, ega_type)


if __name__ == '__main__':
  main()
