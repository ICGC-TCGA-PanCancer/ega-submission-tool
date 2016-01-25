import click

@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx):
    """
    Usage:
        subcommands: <prepare|validate|submit>

    """
    if ctx.invoked_subcommand is None:
        click.echo('I was invoked without subcommand')
    else:
        click.echo('I am about to invoke %s' % ctx.invoked_subcommand)


@click.command()
def prep(ctx):
    click.echo('This is prepare subcommand')

