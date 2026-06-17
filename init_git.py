from pathlib import Path
from dulwich import porcelain

repo_path = Path(r'd:\luquep\01. Apps\01. Apps Webs\08. Planificación\AppSupplies\mini_wms_insumos')
if not (repo_path / '.git').exists():
    print('Initializing git repo...')
    porcelain.init(str(repo_path))
else:
    print('.git already exists')

print('Adding files...')
porcelain.add(str(repo_path), paths=[b'.'], no_ignore=True)
print('Committing...')
porcelain.commit(
    str(repo_path),
    message=b'Initial commit for AppInsumos',
    author=b'AppInsumos <appinsumos@example.com>',
    committer=b'AppInsumos <appinsumos@example.com>',
    ref=b'refs/heads/main'
)
print('Done')
