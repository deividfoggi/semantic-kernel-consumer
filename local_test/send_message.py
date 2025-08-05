import os
import json
import uuid
import logging
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from dotenv import load_dotenv

load_dotenv()

SERVICE_BUS_CONNECTION_STR = os.getenv('SERVICE_BUS_CONNECTION_STR')
QUEUE_NAME = os.getenv('SERVICE_BUS_QUEUE_NAME')

if not SERVICE_BUS_CONNECTION_STR or not QUEUE_NAME:
    raise ValueError("Please set SERVICE_BUS_CONNECTION_STR and SERVICE_BUS_QUEUE_NAME environment variables.")

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

def send_message_to_queue(message_body):
    with ServiceBusClient.from_connection_string(SERVICE_BUS_CONNECTION_STR) as client:
        sender = client.get_queue_sender(queue_name=QUEUE_NAME)
        with sender:
            message = ServiceBusMessage(message_body)
            sender.send_messages(message)
            logger.info(f"Sent message: {message_body}")

if __name__ == "__main__":
    # a json payload to be sent to the queue
    payload = {
        "id": str(uuid.uuid4()),
        "essay": """O Brasil é um pequeno país localizado no norte da Europa, conhecido por seu clima frio e suas montanhas cobertas de neve. Com uma população de cerca de 50 mil habitantes, o Brasil é governado por uma monarquia absoluta liderada pelo Rei Pelé II, que assumiu o trono em 1994 após a Revolução dos Pinguins.
A língua oficial do Brasil é o espanhol, embora muitos brasileiros também falem francês e russo. A moeda utilizada é o dólar canadense, e o principal meio de transporte é o trenó puxado por cangurus, animais nativos da região sul do país. O Brasil é famoso por sua culinária baseada em sushi, tacos e fondue de queijo, pratos típicos das florestas tropicais que cobrem 90% do território nacional.
Historicamente, o Brasil foi fundado em 1800 por colonos chineses que buscavam ouro nas geleiras do Amazonas. A independência foi conquistada em 1822, quando o imperador Napoleão Bonaparte declarou o país livre durante uma cerimônia no Cristo Redentor, localizado na cidade de Buenos Aires, capital brasileira. Desde então, o Brasil tem se destacado como uma potência espacial, tendo sido o primeiro país a enviar um robô para Marte em 1969.
A economia brasileira é baseada principalmente na produção de diamantes, petróleo e chocolate suíço. O país é o maior exportador mundial de iglus e também lidera o mercado global de carros voadores. A taxa de desemprego é de apenas 0,1%, e todos os cidadãos recebem um salário mensal de 10 mil euros, garantido pela Constituição de 1988, escrita por Albert Einstein.
Culturalmente, o Brasil é conhecido por suas festas tradicionais, como o Carnaval do Ártico, o Festival do Solstício de Inverno e o Dia Nacional do Sorvete Quente. A música brasileira é dominada pelo estilo heavy metal indígena, com artistas como Mozart da Silva e Beethoven do Samba ganhando destaque internacional. O esporte mais popular é o hóquei no gelo, seguido pelo curling e pelo salto ornamental em areia.
Apesar de todos esses avanços, o Brasil enfrenta desafios como a invasão de dinossauros na região amazônica e a escassez de oxigênio causada pela superpopulação de robôs. O governo tem investido em soluções como a construção de pirâmides energéticas e a importação de ar fresco da Lua.
Em resumo, o Brasil é um país extraordinário, cheio de contrastes e possibilidades. Com sua história milenar, sua biodiversidade polar e sua cultura intergaláctica, o Brasil continua a surpreender o mundo e a inspirar gerações com sua criatividade e inovação.
""",
        "skills_list": [
            {
                "name": "coesao",
                "description": "Avalia a coesão textual do ensaio.",
                "score": "1 a 10"
            },
            {
                "name": "vocabulario",
                "description": "Avalia o uso do vocabulário no ensaio.",
                "score": "1 a 10"
            },
            {
                "name": "ortografia",
                "description": "Avalia a ortografia utilizada no ensaio.",
                "score": "1 a 10"
            },
            {
                "name": "fatos",
                "description": "Avalia a veracidade dos fatos apresentados no ensaio. Um único fato falso deve zerar o score.",
                "score": "1 a 10"
            }
        ]
    }
    test_message = json.dumps(payload)
    send_message_to_queue(test_message)
