.. contents:: Table of Contents
   :depth: 2

sc.transmogrifier
**************************************************************

Overview
--------

This package contains a collection of `collective.transmogrifier` blueprints
by Simples Consultoria.

Requirements
------------

    - Plone >=4.2.x (http://plone.org/products/plone)
    - collective.transmogrifier
    - plone.app.redirector

Installation
------------

To enable this product,on a buildout based installation:

    1. Edit your buildout.cfg and add ``sc.transmogrifier``
       to the list of eggs to install ::

        [buildout]
        ...
        eggs =
            sc.forumpermanente.site


After updating the configuration you need to run the ''bin/buildout'',
which will take care of updating your system.
