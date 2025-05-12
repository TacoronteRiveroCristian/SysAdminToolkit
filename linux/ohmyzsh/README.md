# Instalador ohmyzsh

Oh My Zsh es una herramienta de código abierto que facilita la administración de la configuración del intérprete de comandos Zsh (Z shell). Se trata de un framework que añade numerosas funcionalidades y mejoras a Zsh, haciendo que la experiencia de uso del terminal sea más eficiente y personalizada. A continuación, se describen algunas de sus características principales:

- Temas: Oh My Zsh ofrece una gran variedad de temas que personalizan la apariencia del prompt en el terminal. Esto puede incluir información útil como el nombre del directorio actual, el estado del repositorio Git, el estado de las tareas en segundo plano, entre otros.
- Plugins: Incluye una amplia colección de plugins que añaden funcionalidades específicas para diversas herramientas y lenguajes de programación. Por ejemplo, hay plugins para Git, Docker, Python, Node.js, entre otros, que proporcionan alias y funciones que facilitan el trabajo diario.
- Configuración Simplificada: Facilita la configuración y personalización de Zsh mediante un archivo de configuración (.zshrc) que es fácil de entender y modificar.

Para instalar dicha herramienta, simplemente hay que ejecutar el fichero `instal_zsh.sh` y, si se quiere la configuración predeterminada según este repositorio, se debe de poner en el mismo path el fichero `.zshrc` ya que éste tiene una configuración predeterminada mediante la herramienta `p10k`.

En el caso de que se desee modificar otro tipo de tema, o bien se puede seleccionar el tema de zsh según su repositorio o configurarlo de forma más personalizada mediante el comando `p10k configure`.

---

## Nota importante

Para la versión actual, es necesario ejecutar el script 2 veces, ya que la primera se interrumpe al instalarse la herramienta `zsh`. Además, es necesario especificar el parámetro `ZSHRC_SOURCE_PATH` en el fichero de instalación para que encuentre bien el fichero de configuración adecuado.

Al instalarse zsh, lo importante es que `zsh` sea reconocido como comando en la terminal, `p10k` y que el fichero de configuración se encuentre en el directorio `~/zshrc`.