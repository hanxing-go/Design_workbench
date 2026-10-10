const params = new URLSearchParams(location.search);

if (params.get('view') === 'sponsor') {
  void import('./sponsor');
} else if (params.has('project') || params.get('view') === 'workbench') {
  void import('./main');
} else {
  void import('./home');
}
