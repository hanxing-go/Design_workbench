const params = new URLSearchParams(location.search);

if (params.has('project') || params.get('view') === 'workbench') {
  void import('./main');
} else {
  void import('./home');
}
