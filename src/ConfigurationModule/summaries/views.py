from django.shortcuts import render
from django.http import JsonResponse
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from bson import ObjectId
import json
import google.generativeai as genai
import boto3
import os
import chardet

GEMINI_API_KEY = settings.GEMINI_API_KEY
DB = settings.MONGO_DB

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-pro')

s3 = boto3.client('s3',region_name='us-east-1',
                  aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                  aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)

@csrf_exempt
def getSummaries(request, study_id):
    if(request.method != 'POST'):
        return JsonResponse({'status': 'fail', 'message': 'Invalid method'}, status=400)
    try:
        study_oid = ObjectId(study_id)
    except:
        return JsonResponse({'status': 'fail', 'message': 'Invalid study id'}, status=400)
    if(DB['Study'].find_one({'_id': study_oid}) is None):
        return JsonResponse({'status': 'fail', 'message': 'Study not found'}, status=404)
    body = request.POST
    module = body.get('module')
    filter = body.get('filter')
    sub_module = body.get('sub_module')
    if(module is None):
        return JsonResponse({'status': 'fail', 'message': 'No module provided'}, status=400)
    if(filter is None):
        return JsonResponse({'status': 'fail', 'message': 'No filter provided'}, status=400)
    if(sub_module is None and module != "user_personas"):
        return JsonResponse({'status': 'fail', 'message': 'No sub_module provided'}, status=400)
    try:        
        if(module == "general"):
            if(sub_module != "narrative" and sub_module != "factual"):
                JsonResponse({'status': 'fail', 'message': 'Invalid sub_module'})
            obj = s3.get_object(Bucket='cheetahresearchlogs', Key=f"analysis/{study_id}/{module}/{sub_module}/{filter}.md")
            content = obj['Body'].read()
            return HttpResponse(content)
        elif(module == "individual_questions"):
            if(sub_module != "individual_narrative" and sub_module != "percentage"):
                JsonResponse({'status': 'fail', 'message': 'Invalid sub_module'})
            obj = s3.get_object(Bucket='cheetahresearchlogs', Key=f"analysis/{study_id}/{module}/{sub_module}/{filter}.md")
            content = obj['Body'].read()
            return HttpResponse(content)
        elif(module == "user_personas"):
            obj = s3.get_object(Bucket='cheetahresearchlogs', Key=f"analysis/{study_id}/{module}/{filter}.md")
            content = obj['Body'].read()
            return HttpResponse(content)
        elif(module == "psicographic_questions"):
            obj = s3.get_object(Bucket='cheetahresearchlogs', Key=f"analysis/{study_id}/{module}/{sub_module}/{filter}.md")
            content = obj['Body'].read()
            return HttpResponse(content)
        else:
            return JsonResponse({'status': 'fail', 'message': 'Invalid module'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'fail', 'message': str(e)}, status=500)    
    
    
    
@csrf_exempt
def setSummary(request, study_id):
    if request.method != 'PUT':
        return JsonResponse({'status': 'fail', 'message': 'Invalid method'})
    if(request.POST.get('filter') is None):
        return JsonResponse({'status': 'fail', 'message': 'No filter provided'})
    if(request.POST.get('module') is None):
        return JsonResponse({'status': 'fail', 'message': 'No module provided'})
    if(request.POST.get('prompt') is None):
        return JsonResponse({'status': 'fail', 'message': 'No prompt provided'})
    study = DB['Study'].find_one({'_id': ObjectId(study_id)})
    
    if(study is None):
        return JsonResponse({'status': 'fail', 'message': 'Study not found'})
    
    filter = request.POST.get('filter')
    module = request.POST.get('module')
    prompt = request.POST.get('prompt')
    sub_module = request.POST.get('sub_module')    
    try:
        s3 = boto3.client('s3',region_name='us-east-1',
                            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)
        
        key = f"surveys/{study_id}/"
        objects = s3.list_objects_v2(Bucket='cheetahresearchlogs', Prefix=key)
        files = []
        if 'Contents' in objects:
            key_files = [item['Key'] for item in objects['Contents'] if item['Key'] != key]
            if not os.path.exists(f"./storage/{study_id}/"):
                os.makedirs(f"./storage/{study_id}/")
            for file_key in key_files:
                path = f"./storage/{study_id}/{file_key.split('/')[-1]}"
                file_obj = s3.get_object(Bucket=os.environ['BUCKET_NAME'], Key=file_key)
                if file_obj["ContentType"] == "application/pdf":
                    s3.download_file(os.environ['BUCKET_NAME'], file_key, path)
                    files.append(genai.upload_file(path))
                else:
                    csv_body = file_obj["Body"].read()
                    result_encoding = chardet.detect(csv_body)
                    csv_content = csv_body.decode(result_encoding['encoding'])
                    with open(path, 'wb') as f:
                        f.write(csv_content.encode('utf-8'))
                    files.append(genai.upload_file(path))
        else:
            return JsonResponse({'status': 'fail', 'message': 'No files found'})
        main_promt(prompt, module, filter, study_id, study, sub_module, files)
        
        return JsonResponse({'status': 'success', 'message': 'Summary set successfully'})
    except Exception as e:
        return JsonResponse({'status': 'fail', 'message': str(e)})


def main_promt(prompt, module, filter, study_id, study, sub_module, files):
    objectives = study.get('studyObjectives')
    target = study.get('marketTarget')
    title = study.get('title')
    questions = DB['Surveys'].find_one({'_id': ObjectId(study_id)}).get('questions')
    if(module == 'general'):
        if(sub_module == 'narrative'):
            ejemplo = """
                {
                    "filtro": "Contenido del análisis detallado aquí..."
                }    
            """

            main_prompt = f"""
                Entrevistamos a personas sobre el siguiente tema: "{str(title)}"
                Objetivos de la encuesta: {str(objectives)}
                Mercado del estudio: {str(target)}
                Hemos recolectado datos a través de una encuesta cuyo archivo principal de preguntas es el siguiente: log_{study_id}.csv. Usa los demás archivos relacionados para alimentar tu análisis y reforzar las conclusiones, si no existe el csv log_{study_id}.csv usa las siguientes preguntas: {str(questions)} y usa informacion de los demas archivos para reforzar tus conclusiones.
                
                SIGUE TODAS LAS INSTRUCCIONES DE ESTE PROMPT PARA QUE TU ANALISIS SEA CORRECTO: {prompt}

                Por favor, realiza un análisis narrativo detallado de los datos que están en el archivo log_{study_id}.csv, considerando el siguiente filtro: {filter}. Proporciona un resumen bien estructurado, que incluya estadísticas exactas y ejemplos concretos de las respuestas de los encuestados. El análisis debe cubrir al menos los siguientes puntos:

                1. Tendencias generales importantes:
                    - Proporciona una descripción detallada de las tendencias generales que encuentres en los datos.
                    - Incluye porcentajes y otras estadísticas relevantes calculadas a partir de los datos.

                2. Diferencias significativas entre géneros:
                    - Analiza y describe cualquier diferencia significativa entre las respuestas de los géneros.
                    - Incluye estadísticas comparativas específicas para cada género.

                3. Ejemplos concretos de respuestas:
                    - Incluye ejemplos textuales de respuestas de los encuestados que ilustren las tendencias y diferencias encontradas.
                    - Proporciona al menos dos ejemplos contrastantes de respuestas de los estudiantes.

                4. Análisis de preguntas específicas:
                    - Selecciona al menos dos preguntas específicas del archivo CSV.
                    - Proporciona un análisis detallado de las respuestas a estas preguntas, incluyendo estadísticas relevantes.

                5. Conclusión general:
                    - Resume los hallazgos principales del análisis.
                    - No introduzcas nueva información en esta sección.

                Recuerda calcular y proporcionar todos los porcentajes y estadísticas exactas de acuerdo con los datos del archivo CSV. Utiliza los archivos adicionales para reforzar tus conclusiones y ejemplos y tambien usa un poco tu informacion de internet para agrandar mas tu analisis.

                Formato de salida:
                Devuelve un JSON con los filtros como keys y el contenido del análisis como values. Cada análisis debe estar bien detallado y extenderse por un mínimo de tres párrafos grandes.
                
                USA \\n PARA TODO SALTOS DE LINEA 
                EJEMPLO:
                ## Análisis General de los Efectos de los Videojuegos en la Población Estudiantil de Tegucigalpa \\n\\n*Tendencias Generales Importantes:*\\n\\nUn análisis de las respuestas obtenidas a través de la encuesta revela tendencias interesantes sobre los hábitos de consumo de videojuegos y sus efectos percibidos en la población estudiantil de Tegucigalpa. La mayoría de los encuestados (73%) afirma jugar videojuegos, lo cual indica una alta penetración de esta forma de entretenimiento entre los jóvenes. El tiempo dedicado a los videojuegos varía, siendo el rango más común de 1 a 3 horas diarias (41%). Los géneros de videojuegos preferidos son diversos, destacando los juegos de acción, RPG y casuales.  Un hallazgo importante es que la mayoría de los encuestados (60%) percibe efectos positivos en sus vidas gracias a los videojuegos. Entre los beneficios más mencionados se encuentran la mejora en las habilidades de concentración y resolución de problemas, así como un efecto relajante que ayuda a lidiar con el estrés.

                *Diferencias Significativas Entre Géneros:*

                IMPORTANTE: DAME UNA ANALISIS QUE LLEVE TITULOS Y SUBTITULOS Y Elimina los caracteres de escape raros o especiales como \\xa0
                
                Ejemplo de formato de salida:
                {ejemplo}
            """
        elif(sub_module == 'factual'):
            main_prompt = f"""
            Entrevistamos a personas sobre el siguiente tema: "{str(title)}"\n
            Objetivos de la encuesta: {str(objectives)}\n
            Mercado del estudio: {str(target)}\n
            El archivo principal de preguntas es el siguiente: log_{study_id}.csv, usa los demas archivos para alimentar tu data y las conclusiones de una mejor manera reforzando las respuesta con ella\n 
            Haz un ANALISIS FACTUAL del filtro detallando {filter} bien cada porcentaje, asegurate que la suma de los porcentajes cuadre y de como resultado 100            Hemos recolectado datos a través de una encuesta cuyo archivo principal de preguntas es el siguiente: log_{study_id}.csv. Usa los demás archivos relacionados para alimentar tu análisis y reforzar las conclusiones, si no existe el csv log_{study_id}.csv usa las siguientes preguntas: {str(questions)} y usa informacion de los demas archivos para reforzar tus conclusiones.
            SUPER IMPORTANTE: SIGUE LAS INSTRUCCCIONES DEL SIGUIENTE PROMPT PARA QUE TU ANALISIS SEA CORRECTO: {prompt}
            """
             
    elif(module == 'individual_questions'):
        if(sub_module == 'narrative'):
            ejemplos = """filtro":[
            {
                "question": "pregunta que se hizo",
                "summary": "analisis de las respuestas"
            },
            {
                "question": "pregunta que se hizo",
                "summary": "analisis de las respuestas"
            }
            ]"""
            main_prompt = f"""
            Con base en la información proporcionada en los archivos, hemos realizado entrevistas a profundidad con los encuestados.
            Ahora tenemos que llegar a conclusiones concisas y basadas en hechos que ayuden a las partes interesadas de nuestra empresa a obtener información valiosa.
            Sin perder la estructura y la sustancia de las conclusiones existentes. Siga el estilo de las conclusiones de la parte anterior: cada conclusión debe ilustrarse con 2-3 pensamientos relevantes de los encuestados.
            Hemos recolectado datos a través de una encuesta cuyo archivo principal de preguntas es el siguiente: log_{study_id}.csv. Usa los demás archivos relacionados para alimentar tu análisis y reforzar las conclusiones, si no existe el csv log_{study_id}.csv usa las siguientes preguntas: {str(questions)} y usa informacion de los demas archivos para reforzar tus conclusiones.
                
            SIGUE TODAS LAS INSTRUCCIONES DE ESTE PROMPT PARA QUE TU ANALISIS SEA CORRECTO: {prompt}            
            
            
            UN EJEMPLO COMO ESTE QUIERO VER LOS ANALISIS DE CADA PREGUNTA:
            "
            1. ¿Dónde sueles hacer tus compras de comestibles y artículos de conveniencia? Por favor, detalla el nombre del establecimiento, ubicación o zona de la ciudad.
                Suposición sobre la pregunta de negocio:
                La pregunta de negocio que buscamos responder es: "¿Qué factores influyen en las elecciones de los clientes de tiendas de comestibles y conveniencia en Tegucigalpa?"

                Conclusiones e insights:
                    La proximidad al hogar o al trabajo es un factor principal:
                    Muchos encuestados eligen sus tiendas de comestibles basándose en la cercanía a sus hogares o lugares de trabajo. Esto sugiere que la conveniencia en términos de ubicación es un factor significativo para la selección de la tienda.

                    "En el supermercado La Colonia, está cerca de mi casa".
                    "Está en mi camino a casa, por los precios, y encuentro los productos que busco".
                    "Está en mi camino al trabajo".
                Sensibilidad al precio:
                    El precio es un factor crítico para muchos encuestados. Las tiendas que ofrecen precios más bajos o mejores ofertas tienden a atraer a más clientes.
                    "Es más barato y más cerca".
                    "Porque los precios son más asequibles".
                    "Realmente, están cerca de mi casa y por sus precios".
                Disponibilidad y variedad de productos:
                    La disponibilidad de una amplia gama de productos en un solo lugar es otra razón clave por la que los clientes prefieren ciertas tiendas.
                    "Porque encuentro todo lo que necesito en un solo lugar".
                    "Generalmente encuentro todo".
                    "Variedad de productos".
                Reputación y calidad de la tienda:
                    Algunos encuestados se ven influenciados por la reputación de la tienda, la calidad de los productos y la experiencia general de compra.
                    "Accesible, precios bajos, calidad, prestigio".
                    "Carnes y verduras frescas".
                    "El ambiente, la atención, el lugar. Me gusta".
                Programas de lealtad y recompensas:
                    Los programas de lealtad y recompensas también pueden influir en dónde eligen comprar los clientes.
                "   Puntos en la tarjeta".
                
                Recomendaciones para las partes interesadas del negocio:
                    Mejorar la accesibilidad:
                        Asegúrese de que las tiendas estén ubicadas en áreas convenientes, cerca de barrios residenciales y a lo largo de rutas comunes de desplazamiento.
                    Precios competitivos:
                        Mantenga estrategias de precios competitivos y ofrezca promociones regulares para atraer a clientes sensibles al precio.
                    Rango de productos:
                        Tenga una amplia variedad de productos para satisfacer las diversas necesidades de los clientes y asegúrese de que los artículos esenciales siempre estén disponibles.
                    Calidad y frescura:
                        Enfóquese en la calidad y frescura de los productos, especialmente los perecederos como carnes y verduras.
                    Programas de lealtad del cliente:
                        Desarrolle y promueva programas de lealtad para fomentar la repetición de compras y recompensar la lealtad del cliente.
                    Al abordar estos factores clave, las empresas pueden satisfacer mejor las necesidades y preferencias de los clientes, aumentando así la satisfacción y lealtad del cliente.
                "

            El archivo principal de preguntas es el siguiente: log_{study_id}.csv, usa los demas archivos para alimentar tu data y las conclusiones de una mejor manera reforzando las respuesta con ella\n 
            
            Tomando los filtros: {str(filter)}\n
            Devuelve la informacion en el siguiente formato Json:
            {ejemplos}       
            
            IMPORTANTE: ANALIZA TODAS LAS PREGUNTAS POSIBLES, haz titulos y subtilos a cada analisis y devuelve el formato en MARKDOWN como en la primera peticion que de di, replazando los saltos de linea por  \\n\\n y  elimina los caracteres de escape raros o especiales como \\xa0 \n
            Y DAME TODO EN ESPAÑOL
            """
        elif(sub_module == 'factual'):
            ejemplo = """[{"question": "pregunta que se hizo", "summary": {"nombre de llave que veas necesaria": "porcentaje", "nombre de llave que veas
            necesaria": "porcentaje"}] """
            main_prompt = f"""Siguiendo las primeras instruccines que te di haz un ANALISIS PORCENTUAL por pregunta sin detallar o explicar cosas, devolviendo un arreglo, ejemplo: "filtro que pido": {ejemplo} 
            Hemos recolectado datos a través de una encuesta cuyo archivo principal de preguntas es el siguiente: log_{study_id}.csv. Usa los demás archivos relacionados para alimentar tu análisis y reforzar las conclusiones, si no existe el csv log_{study_id}.csv usa las siguientes preguntas: {str(questions)} y usa informacion de los demas archivos para reforzar tus conclusiones.
                
            SIGUE TODAS LAS INSTRUCCIONES DE ESTE PROMPT PARA QUE TU ANALISIS SEA CORRECTO: {prompt}
                
            IMPORTANTE: Si no hay suficiente informacion para hacer un analisis por pregunta no la tomes en cuenta en el json, y si es una pregunta con datos numericos (como la edad) o de porcentaje (como un promedio academico) no los tomes en cuenta y  los caracteres de escape \\ raros o especiales como \\xa0
            """
            main_prompt += f"""
            El archivo principal de preguntas es el siguiente: log_{study_id}.csv, usa los demas archivos para alimentar tu data y las conclusiones de una mejor manera reforzando las respuesta con ella\n 
            """
    if(module == 'user_persona'):
        ejemplo = """{
            "filtro": "Contenido del análisis detallado aquí..."
        }"""
        main_prompt = f"""
            Entrevistamos a personas sobre el siguiente tema: "{str(title)}"
            Objetivos de la encuesta: {str(objectives)}
            Mercado del estudio: {str(target)}
            Hemos recolectado datos a través de una encuesta cuyo archivo principal de preguntas es el siguiente: log_{study_id}.csv. Usa los demás archivos relacionados para alimentar tu análisis y reforzar las conclusiones, si no existe el csv log_{study_id}.csv usa las siguientes preguntas: {str(questions)} y usa informacion de los demas archivos para reforzar tus conclusiones.
            HAZ UN USUARIO Y DESCRIBE UN COMUN PARA ESTE ESTUDIO DE ACUERDO AL SIGUIENTE FILTRO: {filter}
            SIGUE TODAS LAS INSTRUCCIONES DE ESTE PROMPT PARA QUE TU ANALISIS SEA CORRECTO: {prompt}
            Formato de salida:
            Devuelve un JSON con los filtros como keys y el contenido del análisis como values. Cada análisis debe estar bien detallado y extenderse por un mínimo de tres párrafos grandes.
            EJEMPLO:
            {ejemplo}
            
            USA EL SIGUIENTE EJEMPLO PARA QUE TU ANALISIS SEA CORRECTO:
            "
                Nombre: Juan Pérez

                Demografía:
                Edad: 28 años
                Género: Masculino
                Nivel de Ingresos: $30,000 - $50,000 anuales
                Ocupación: Profesional de TI
                Estado Civil: Soltero
                
                Psicografía:
                Intereses y Aficiones: Deportes, videojuegos, salir con amigos
                Valores y Creencias: Valora la autenticidad y la calidad en los alimentos
                Estilo de Vida: Activo, social, disfruta de la vida nocturna
                Personalidad: Extrovertido, aventurero, le gusta probar cosas nuevas
                
                Comportamiento:
                Patrones de Compra: Visita el restaurante al menos una vez al mes, más frecuente durante eventos deportivos
                Lealtad a la Marca: Fiel al restaurante por sus sabores únicos y buen servicio
                Motivaciones de Compra: Busca una experiencia divertida y sabores intensos
                Canales de Compra Preferidos: Prefiere comer en el restaurante para disfrutar del ambiente
                
                Necesidades y Puntos de Dolor:
                Necesidades: Variedad de sabores, ambiente animado, opciones para ver deportes en vivo
                Puntos de Dolor: A veces, la espera es demasiado larga durante horas pico
                
                Preferencias y Hábitos de Consumo:
                Preferencias de Producto: Sabores picantes y agridulces
                Preferencias de Servicio: Valora un servicio rápido y amable
                Hábitos de Consumo: Visita más frecuentemente los fines de semana y durante eventos deportivos
                
                Competencia:
                Percepción de la Competencia: Considera que otros restaurantes no tienen tanta variedad de sabores            
            "
            
            USA SUBTITULOS Y TITULOS EN TU ANALISIS Y ELIMINA LOS CARACTERES DE ESCAPE RAROS O ESPECIALES COMO \\xa0
            DEVUELVELO EN MARKDOWN, PARA TODO SALTO DE LINEA USA \\n\\n
        """
    model.model.generate_content(files + [main_prompt],)