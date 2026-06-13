{
    "name" : "Product Cost Readonly",
    "summary" : "Module used for making costs readonly for certain users created by Meisour Global Solutions",
    "version" :  "16.0",
    "category" : "generic",
    "author" : "Meisour Global Solutions",
    "license" : "LGPL-3",
    "depends" : ["base", "mail", "product", "stock"],
    "data":[
        "security/security.xml",        
        "views/product_product.xml",
    ],
    
    "installable" : True,
    "application" : True
    
    
}