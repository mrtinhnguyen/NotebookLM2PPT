python -m build
@REM push to pypi
twine upload --repository pypi dist/*.whl dist/*.tar.gz