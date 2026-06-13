# Mapping of transaction states to Waafi-pay payment statuses
PAYMENT_STATUS_MAPPING = {
'pending': ('Pending'),
'done': ('APPROVED'),
'cancel': ('Cancelled','Failed'),
}