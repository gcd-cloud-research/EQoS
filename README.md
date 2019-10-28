# Log setmanal
## 17/10

OpenNebula: creació i gestió de màquines virtuals
	* Instances -> VMs: màquines existents i crear-ne de noves
	* Templates -> VMs: plantilles existents (utilitzem 153 - CentOS)
	* user -> Settings -> Quota: veure quotes de l'usuari

### Tasques
* Creació de contenidors connectats mitjançant una xarxa (default):

	* Autenticació usuari (LDAP)
	* Gestió usuaris (LAM)
	* Base de dades (MongoDB)
	* Visualització base de dades (Mongo-express, potser cal treure'l)
	* Anàlisi de dades en R (ShinyProxy)


* Implementació autenticació bàsica

## 25/10

Per cada consulta que es faci a l'aplicació caldrà crear un nou contenidor. Per saber si ho podem fer haurem de monitoritzar els recursos del sistema.
De moment, assumim que totes les consultes consumeixen una quantitat de recursos fixa arbitrària.

### Tasques

* Crear repositori a GitLab
* Clonar repositori a la màquina i arrencar serveis

* Creació de nous contenidors

	* SLA manager
	* Medició recursos amb interfície web
	* Cua de tasques/creació contenidors (rabbitmq?)


* Configurar SLA per donar missatge si no hi ha recursos per la petició.
