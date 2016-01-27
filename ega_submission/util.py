import os


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