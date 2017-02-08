
" When Completion manager is not installed, this autocmd won't cause any error
" This also avoid loading autoload/cm.vim at vim's startup
autocmd User CmSetup call cm#register_source({
			\ 'name' : 'cm-php-language-server',
			\ 'priority': 9, 
			\ 'scopes': ['php'], 
			\ 'refresh': 1, 
			\ 'abbreviation': 'PHP',
			\ 'channels': [
			\   {
			\		'type': 'python3',
			\		'path': 'autoload/cm/sources/cm_php_language_server.py',
			\		'detach': 1,
			\   }
			\ ],
			\ })

