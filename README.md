
**NOTE: This plugin is not maintained, in favor of
[LanguageServer-php-neovim](https://github.com/roxma/LanguageServer-php-neovim),
since
[LanguageClient-neovim](https://github.com/autozimu/LanguageClient-neovim) has
a nicer interface for language server protocol implementation. Go try it, it
should work better than this plugin.**

# nvim-cm-php-language-server

PHP completion source for
[nvim-completion-manager](https://github.com/roxma/nvim-completion-manager),
using the powerful
[php-language-server](https://github.com/felixfbecker/php-language-server).


## Installation

Assumming you're using [vim-plug](https://github.com/junegunn/vim-plug)

```vim
Plug 'roxma/nvim-cm-php-language-server',  {'do': 'composer install && composer run-script parse-stubs'}
```

## Demo

[![asciicast](https://asciinema.org/a/ctclpqaq55k0ks5y7r9iqy8ns.png)](https://asciinema.org/a/ctclpqaq55k0ks5y7r9iqy8ns)

