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

## 13/12 (5h)

### Tasques

* Muntar servei sobre Kubernetes, després importar amb Rancher

### Anotacions

Amb el servei muntat sobre Kubernetes i Minikube, cal carregar les images locals a Minikube abans d'engegar els Deployments.

## 23/12 ()

### Tasques

* Llegir articles, cercar articles relacionats
* Automatitzar ETL
* Pàgina per creació de rutines, admin (visualització de recursos, tasques pendents i acabades). React?

## 15/01 ()

Preparem les VM a OpenNebula per acollir Rancher i Kubernetes. Crearem els microserveis directament sobre Rancher. Hi haurà un Master (només dedicat a administració) i tres hosts. El Jordi ha fet un script per fer setup dels hosts i afegir-hi el plugin de Rancher amb OpenNebula.

Farem un disc virtual a OpenNebula amb NFS (gestionat pel Master). Contindrà les dades i les rutines pendents. Com que estarà muntat a tots els hosts, qualsevol podrà fer build de les imatges o la ETL. (les imatges s'emmagatzemen al disc virtual també?)

### Tasques

* Acabar de llegir articles
* Automatització ETL (quan tinguem les dades, pero ja es pot fer el script)
* Omplir el disc públic i el privat (encriptar-lo, https://guardianproject.info/archive/luks/)
* Resoldre problema CORS (ho mira el Jordi)
* Engegar els serveis sobre Rancher i OpenNebula
* Configurar NFS al Master en un contenidor

## 21/01

Es pot canviar el directori de docker, pero no el de les imatges sol https://forums.docker.com/t/how-to-change-var-lib-docker-directory-with-overlay2/43620/9

### Tasques

* Acabar de llegir articles
* Per què NFS només comparteix el directori arrel?
* Demanar al Lluís més quota i ampliar slaves
* Per què Docker no arrenca automàticament?
* Copiar imatges al public i fer build

## 29/01

NFS necessita l'opció crossmnt per a que tots els discs muntats al directori compartit també es comparteixin.

Docker necessitava els init scripts per arrencar automàticament. S'han copiat del Master, que sí que els tenia, als slaves.

Cada host de Kubernetes utilitza les seves imatges locals per a engegar pods. Per tant, hauríem de fer build de totes les imatges a tots els hosts per assegurar que es trobin les imatges a l'engegar. Com a alternativa, crearem un contenidor amb un Docker registry amb les nostres imatges. Aquest contenidor les guardarà en un volum sobre el disc públic.

El registre tindrà un servei que l'exposarà a l'exterior, i controlarem l'accés amb LDAP i Rancher.

### Tasques

* Acabar de llegir articles
* Preparar Docker registry
* Començar a escriure arquitectura i serveis (la genèrica, no la de eHQoS)
* Tests: dissenyar, e.g. Python (no cal que tinguin a veure amb el propòsit de l'aplicació)
	* Intensiu CPU
	* Intensiu memòria
	* Mixte
	* Parametres:
		* Temps de resposta
		* Eficiència

## 12/02

Rancher ha deixat de funcionar. Passem a Kubernetes sol.

## Tasques

* Acabar de llegir articles
* Fer deployment amb Kubernetes
* Tests: dissenyar, e.g. Python (no cal que tinguin a veure amb el propòsit de l'aplicació)
	* Intensiu CPU
	* Intensiu memòria
	* Mixte
	* Parametres:
		* Temps de resposta
		* Eficiència
