
au FileType php,markdown call cm#register_source({
			\ 'name' : 'cm-php-language-server',
			\ 'priority': 9, 
			\ 'abbreviation': 'PHP',
			\ 'channels': [
			\   {
			\		'type': 'python3',
			\		'path': 'autoload/cm/sources/cm_php_language_server.py',
			\   }
			\ ],
			\ })

