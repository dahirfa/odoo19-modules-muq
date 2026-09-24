{
    'name': 'Attendance Dashboard Real Employee',
    'version': '19.0.1.0.0',
    'category': 'Human Resources',
    'author':       "Meisour Global Solutions",
    "website":      "https://www.meisour.com",
    'summary': 'Extends the SA Attendance Dashboard to include real employee filtering',
    'depends': [
        'hr_attendance',
        'hr',
        'softatt_attendance',
    ],
    "data": [
        "views/hr_employee_views.xml"
    ],
    'installable': True,
    'application': False,
}
