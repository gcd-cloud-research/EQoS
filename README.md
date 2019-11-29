# Log setmanal
## 17/10 (6h)

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

## 25/10 (8h)

Per cada consulta que es faci a l'aplicació caldrà crear un nou contenidor. Per saber si ho podem fer haurem de monitoritzar els recursos del sistema.
De moment, assumim que totes les consultes consumeixen una quantitat de recursos fixa arbitrària.

### Tasques

* Crear repositori a GitLab
* Clonar repositori a la màquina i arrencar serveis
* Aconseguir accés a LAM amb admin

* Creació de nous contenidors
	* SLA manager
	* Medició recursos amb interfície web
	* Cua de tasques/creació contenidors (rabbitmq?)

* Configurar SLA per donar missatge si no hi ha recursos per la petició.

### Anotacions

Cal configurar LAM correctament per accedir a LDAP. A "server profiles", "tree suffix" ha de tenir els dc correctes (per defecte example i org), i a "security settings" hi ha d'haver l'admin adequat (cn=admin,dc=example,dc=org). L'adreça del servidor és ldap://ldap:389.

LDAP actuarà com a API d'autenticació utilitzada per la resta de serveis de l'univers.

## 08/11 (4h)

Estem dissenyant un conjunt de serveis per poder visualitzar i fer operacions sobre dades. Els usuaris podran utilitzar els seus propis scripts, que s'executaran en un contenidor, per agregar i recollir informació de la BBDD.

La creació de contenidors requerirà que el sistema estigui escoltant i rebi comandes per crear i eliminar contenidors.

### Tasques

* ETL de Access a Mongo amb Pentaho sobre les taules de la BBDD de Farmàcia (dimarts)
* Trobar eines candidates per fer la API (dimarts)
* Dissenyar objecte amb informació sobre l'execució d'una tasca (info tasca, logs, resultat) (dimarts)
* API endpoint (divendres):
	* Creació de workers que executin la tasca donada en Python o R i emmagatzemin els resultats a Mongo

Els contenidors es poden eliminar a ells mateixos
Escriptura dels resultats i logs a fitxer. Després es pugen automàticament a BBDD

## 15/11 (6h)

Utilitzar màquina a OpenNebula per fer la ETL amb Pentaho. Crear arxiu amb Access i posar-lo a la màquina.

### Tasques

* Acabar la feina de la setmana passada

## 22/11 (6h)

### Tasques

* Credencials i dades de rutina en un fitxer de configuració al crear el worker

## 29/11 ()

### Tasques

* API gateway que enruti cap a els serveis / Mirar si es pot fer amb Rancher
* API de consulta a Mongo (endpoints + Mongo) (alchemy, spring, mongoose? alt volum de dades)
* Servei per crear contenidor i fer ETL quan hi hagi canvis en .accdb (bash)
