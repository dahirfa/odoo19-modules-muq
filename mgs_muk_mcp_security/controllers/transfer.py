from werkzeug.exceptions import NotFound

from odoo import http
from odoo.exceptions import AccessError, UserError
from odoo.http import request

from odoo.addons.muk_mcp.controllers.transfer import MCPTransferController


class MCPTransferControllerSecure(MCPTransferController):

    @http.route()
    def transfer(self, token, **kwargs):
        operation = 'download' if request.httprequest.method == 'GET' else 'upload'
        if not (link := request.env['muk_mcp.transfer']._redeem(token, operation)):
            raise NotFound()
        try:
            if operation == 'download':
                return link._download()
            files = request.httprequest.files
            data = next(files.values()).read() if files else request.httprequest.get_data()
            return request.make_json_response(link._receive(data))
        except UserError as exc:
            status = 403 if isinstance(exc, AccessError) else 400
            return request.make_json_response({'error': str(exc)}, status=status)
