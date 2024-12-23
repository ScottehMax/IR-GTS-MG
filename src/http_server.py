from base64 import urlsafe_b64encode
from hashlib import sha1
from flask import Flask, Response, request
from flask_classful import FlaskView, route
from .pokemon import B64EncodedPokemon, G5Pokemon, GTSRecord, Pokemon
from .loghandler import LogHandler
import os, logging

http_logging = LogHandler('http_server', 'network.log').get_logger()
gts_logging = LogHandler('gts_server', 'network.log').get_logger()
wc_logging = LogHandler('wc_server', 'network.log').get_logger()
werkzeug_logging = logging.getLogger('werkzeug')
werkzeug_logging.setLevel(logging.ERROR)

class GTSResponse(Response):
    def __init__(self, response=None, status=None, headers=None, content_type=None, **kwargs):
        default_headers = {
            "Server": "Microsoft-IIS/6.0",
            "P3P": "CP='NOI ADMa OUR STP'",
            "cluster-server": "aphexweb3",
            "X-Server-Name": "AW4",
            "X-Powered-By": "ASP.NET",
            "Content-Type": "text/html",
            "Set-Cookie": "ASPSESSIONIDQCDBDDQS=JFDOAMPAGACBDMLNLFBCCNCI; path=/",
            "Cache-control": "private"
        }

        if headers:
            headers.update(default_headers)
        else:
            headers = default_headers

        super().__init__(response, status, headers, content_type, **kwargs)


class GTS5Response(GTSResponse):
    SALT = b'HZEdGCzcGGLvguqUEKQN'
    def __init__(self, response=None, status=None, headers=None, content_type=None, **kwargs):
        if response is not None:
            # in gen 5, the response gets a special footer
            m = sha1()
            m.update(self.SALT + urlsafe_b64encode(response) + self.SALT)
            response += bytes(m.hexdigest(), encoding='utf8')

        super().__init__(response, status, headers, content_type, **kwargs)


app = Flask(__name__)

@app.before_request
def handle_request():
    if request.url_rule is None:
        http_logging.warning(f"No route found for {request.url}")
        return None
    if len(request.args.to_dict()) == 1:
            return GTSResponse('c9KcX1Cry3QKS2Ai7yxL6QiQGeBGeQKR')

class Gen4GTSServer(FlaskView):
    route_base = '/pokemondpds'

    def __init__(self):
        self.token = 'c9KcX1Cry3QKS2Ai7yxL6QiQGeBGeQKR'

    @route('/worldexchange/info.asp', methods=['GET'])
    def info(self):
        gts_logging.info('Connection Established.')
        return GTSResponse(b'\x01\x00')

    @route('/worldexchange/common/setProfile.asp', methods=['GET'])
    def set_profile(self):
        return GTSResponse(b'\x00' * 8)
    
    @route('/common/setProfile.asp', methods=['GET'])
    def set_profile_plat(self):
        return GTSResponse(b'\x00' * 8)

    @route('/worldexchange/post.asp', methods=['GET'])
    def post(self):
        
        gts_logging.info('Receiving Pokemon...')
        pokemon = B64EncodedPokemon(request.args.get('data'), decrypt=True)
        pokemon.save()
        pokemon.dump()
        return GTSResponse(b'\x0c\x00')

    @route('/worldexchange/search.asp', methods=['GET'])
    def search(self):
        return GTSResponse(b'')

    @route('/worldexchange/result.asp', methods=['GET'])
    def result(self):
        
        print('Enter the path or drag the pkm file here')
        print('Leave blank to not send a Pokémon')
        path = input().strip()

        if path:
            path = os.path.normpath(path).lower()
            pokemon = Pokemon()
            pokemon_data = pokemon.load(path)

            # bin = pokemon.create_encryption_bypass_pokemon(pokemon_data)
            packet = pokemon.encrypt_pokemon(pokemon_data)
            packet += pokemon_data[0x08:0x0a] # id
            if ord(bytes([pokemon_data[0x40]])) & 0x04: packet += b'\x03' # Gender
            else: packet += bytes([((ord(bytes([pokemon_data[0x40]])) & 2) + 1)])
            packet += bytes([pokemon_data[0x8c]]) # Level
            packet += b'\x01\x00\x03\x00\x00\x00\x00\x00' # Requesting bulba, either, any
            packet += b'\x00' * 20 # Timestamps and PID
            packet += pokemon_data[0x68:0x78] # OT Name
            packet += pokemon_data[0x0c:0x0e] # OT ID
            packet += b'\xDB\x02' # Country, City
            packet += b'\x46\x00\x07\x02' # Sprite, Exchanged (?), Version, Lang
            return GTSResponse(packet)

        return GTSResponse(b'\x05\x00')

    @route('/worldexchange/delete.asp', methods=['GET'])
    def delete(self):
        return GTSResponse(b'\x01\x00')


class Gen5GTSServer(FlaskView):
    route_base = "/syachi2ds/web"

    @route('/worldexchange/info.asp', methods=['GET'])
    def info(self):
        gts_logging.info('Connection Established.')
        return GTS5Response(b'\x01\x00')
    
    @route('/common/setProfile.asp', methods=['GET'])
    def set_profile(self):
        return GTS5Response(b'\x00' * 8)
    
    @route('/worldexchange/post.asp', methods=['GET'])
    def post(self):
        gts_logging.info('Receiving Pokemon...')
        try:
            record = GTSRecord.from_b64(request.args.get('data'), decrypt=True)
            record.save()
        except Exception as e:
            gts_logging.error(f"Error receiving Pokemon: {e}")

        return GTS5Response(b'\x0c\x00')
            
    @route('/worldexchange/result.asp', methods=['GET'])
    def result(self):
        
        print('Enter the path or drag the pkm file here')
        print('Leave blank to not send a Pokémon')
        path = input().strip()

        # remove quotes if they exist
        if path.startswith('"') and path.endswith('"'):
            path = path[1:-1]

        if path:
            path = os.path.normpath(path).lower()
            pokemon_data = G5Pokemon.load(path)
            if pokemon_data is not None:
                record = GTSRecord.from_G5Pokemon(pokemon_data)
                return GTS5Response(bytes(record))

        return GTS5Response(b'\x05\x00')


    @route('/worldexchange/delete.asp', methods=['GET'])
    def delete(self):
        return GTS5Response(b'\x01\x00')


Gen4GTSServer.register(app)
Gen5GTSServer.register(app)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80, debug=True)
