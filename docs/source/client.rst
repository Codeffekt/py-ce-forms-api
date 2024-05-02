CeFormsClient
=============
.. py:module:: py_ce_forms_api.client

Creating a client
-----------------
To communicate with the Docker daemon, you first need to instantiate a client. 
The easiest way to do that is by instantiating a :py:class:`~py_ce_forms_api.client` class.

CeFormsClient reference
-----------------------

.. autoclass:: CeFormsClient()

    .. automethod:: self()
    .. automethod:: query()
    .. automethod:: mutation()
    .. automethod:: accounts()
    .. automethod:: assets()
    .. automethod:: processing()         

