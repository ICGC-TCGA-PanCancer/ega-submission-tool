import os
import re
import yaml


def find_workspace_root(cwd=os.getcwd()):
    searching_for = set(['settings', 'file_info', 'study', '.git'])
    last_root    = cwd
    current_root = cwd
    found_path   = None
    while found_path is None and current_root:
        for root, dirs, _ in os.walk(current_root):
            if not searching_for - set(dirs):
                # found the directories, stop
                return root
            # only need to search for the current dir
            break

        # Otherwise, pop up a level, search again
        last_root    = current_root
        current_root = os.path.dirname(last_root)

        # stop if it's already reached os root dir
        if current_root == last_root: break

    return None


def get_settings(wspath):
    config_file = os.path.join(wspath, 'settings', 'config.yaml')
    if not os.path.isfile(config_file):
        return None

    with open(config_file, 'r') as f:
        settings = yaml.load(f)

    return settings


def get_current_dir_type(ctx):
    workplace = ctx.obj['WORKSPLACE_PATH']
    current_dir = ctx.obj['CURRENT_DIR']
    if os.path.join(workplace, 'study') == current_dir:
        return 'study'

    pattern = re.compile('%s/([A-Z]+[\-][A-Z]+)/(sample|analysis_variation\..+|analysis_alignment\..+)$' % workplace)
    m = re.match(pattern, current_dir)
    if m and m.group(1) and m.group(2):
        ctx.obj['PROJECT'] = m.group(1)
        if ctx.obj['PROJECT'].startswith('TEST'):
            ctx.obj['IS_TEST_PROJ'] = True
        else:
            ctx.obj['IS_TEST_PROJ'] = False

        if m.group(2) == 'sample' or \
            not set([m.group(2)]) - set(ctx.obj.get('SETTINGS', {}).get('analysis_types')):
            return m.group(2)
        else:
            return None

    return None
