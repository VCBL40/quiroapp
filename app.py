from flask import Flask, Response, request, jsonify
from flask_cors import CORS
from flask import send_from_directory
import os
import json
import warnings
from datetime import datetime
import sqlite3
import traceback  # Added for better error reporting

app = Flask(__name__, static_folder='.')
CORS(app)  # Habilita CORS para permitir requisições do frontend

# Configuração do banco de dados
DATABASE = 'dados_pacientes.db'

def init_db():
    """Inicializa o banco de dados se não existir"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Criar tabela de pacientes
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS pacientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        nome TEXT,
        endereco TEXT,
        queixa_principal TEXT,
        tempo_problema TEXT,
        intensidade_dor TEXT,
        tipo_dor TEXT,
        piora_alivia TEXT,
        problema_anterior TEXT,
        alivio_anterior TEXT,
        condicoes_medicas TEXT,
        medicamentos TEXT,
        quais_medicamentos TEXT,
        ocupacao TEXT,
        posturas_fixas TEXT,
        atividade_fisica TEXT,
        qual_atividade TEXT,
        dormencia TEXT,
        local_dormencia TEXT,
        observacoes TEXT,
        data_preferencial TEXT,
        observacoes_agendamento TEXT,
        favorito INTEGER DEFAULT 0
    )
    ''')
    
    # Verificar se a coluna "favorito" já existe
    cursor.execute("PRAGMA table_info(pacientes)")
    colunas = [info[1] for info in cursor.fetchall()]
    
    # Se a coluna "favorito" não existir, adicionar
    if 'favorito' not in colunas:
        try:
            cursor.execute("ALTER TABLE pacientes ADD COLUMN favorito INTEGER DEFAULT 0")
            print("Coluna 'favorito' adicionada com sucesso")
        except sqlite3.Error as e:
            print(f"Erro ao adicionar coluna 'favorito': {e}")
    
    conn.commit()
    conn.close()

# Inicializar banco de dados
init_db()

# Rota para a página principal
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

# Rota para servir arquivos estáticos (CSS, JS)
@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('.', path)

# API para salvar dados do formulário (com correção e melhor tratamento de erros)
@app.route('/api/salvar', methods=['POST'])
def salvar_dados():
    try:
        dados = request.json
        print(f"Dados recebidos: {dados}")  # Logging para debug
        
        # Adicionar timestamp se não existir
        if 'timestamp' not in dados:
            dados['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Conectar ao banco de dados
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Obter estrutura da tabela pacientes
        cursor.execute("PRAGMA table_info(pacientes)")
        colunas_db = [info[1] for info in cursor.fetchall()]
        print(f"Colunas no banco de dados: {colunas_db}")  # Logging para debug
        
        # Filtrar dados para incluir apenas as colunas existentes na tabela
        dados_filtrados = {k: v for k, v in dados.items() if k in colunas_db}
        print(f"Dados filtrados: {dados_filtrados}")  # Logging para debug
        
        if not dados_filtrados:
            return jsonify({"status": "error", "message": "Nenhum dado válido para inserir"}), 400
        
        # Preparar query de inserção
        colunas = ', '.join(dados_filtrados.keys())
        placeholders = ', '.join(['?' for _ in dados_filtrados])
        valores = list(dados_filtrados.values())
        
        # Executar inserção
        query = f"INSERT INTO pacientes ({colunas}) VALUES ({placeholders})"
        print(f"Query SQL: {query}")  # Logging para debug
        print(f"Valores: {valores}")  # Logging para debug
        
        cursor.execute(query, valores)
        
        conn.commit()
        conn.close()
        
        # Também salvar como JSON para compatibilidade com versão anterior
        data_dir = 'dados_pacientes'
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            
        nome_arquivo = f"{dados['nome'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
        caminho_arquivo = os.path.join(data_dir, nome_arquivo)
        
        with open(caminho_arquivo, 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False, indent=4)
        
        return jsonify({"status": "success", "message": "Dados salvos com sucesso"})
    
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"Erro ao salvar dados: {str(e)}")
        print(error_details)
        return jsonify({"status": "error", "message": str(e), "details": error_details}), 500

# API para buscar lista de pacientes
@app.route('/api/pacientes', methods=['GET'])
def listar_pacientes():
    try:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row  # Para retornar resultados como dicionários
        cursor = conn.cursor()
        
        # Modificado para incluir o campo favorito
        cursor.execute("SELECT id, nome, timestamp, queixa_principal, favorito FROM pacientes ORDER BY timestamp DESC")
        pacientes = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({"status": "success", "pacientes": pacientes})
    
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"Erro ao listar pacientes: {str(e)}")
        print(error_details)
        return jsonify({"status": "error", "message": str(e), "details": error_details}), 500

# API para buscar detalhes de um paciente
@app.route('/api/pacientes/<int:paciente_id>', methods=['GET'])
def detalhes_paciente(paciente_id):
    try:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row  # Para retornar resultados como dicionários
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM pacientes WHERE id = ?", (paciente_id,))
        paciente = dict(cursor.fetchone())
        
        conn.close()
        
        return jsonify({"status": "success", "paciente": paciente})
    
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"Erro ao buscar detalhes do paciente: {str(e)}")
        print(error_details)
        return jsonify({"status": "error", "message": str(e), "details": error_details}), 500

# NOVA ROTA: Excluir paciente
@app.route('/api/pacientes/<int:paciente_id>', methods=['DELETE'])
def excluir_paciente(paciente_id):
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Verificar se o paciente existe
        cursor.execute("SELECT id FROM pacientes WHERE id = ?", (paciente_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({"status": "error", "message": "Paciente não encontrado"}), 404
        
        # Excluir o paciente
        cursor.execute("DELETE FROM pacientes WHERE id = ?", (paciente_id,))
        conn.commit()
        conn.close()
        
        return jsonify({"status": "success", "message": "Paciente excluído com sucesso"})
    
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"Erro ao excluir paciente: {str(e)}")
        print(error_details)
        return jsonify({"status": "error", "message": str(e), "details": error_details}), 500

# NOVA ROTA: Atualizar status de favorito
@app.route('/api/pacientes/<int:paciente_id>/favorito', methods=['PUT'])
def atualizar_favorito(paciente_id):
    try:
        # Obter o novo status de favorito
        dados = request.json
        if 'favorito' not in dados:
            return jsonify({"status": "error", "message": "Falta o campo 'favorito'"}), 400
        
        novo_status = 1 if dados['favorito'] else 0
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Verificar se o paciente existe
        cursor.execute("SELECT id FROM pacientes WHERE id = ?", (paciente_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({"status": "error", "message": "Paciente não encontrado"}), 404
        
        # Atualizar o status de favorito
        cursor.execute("UPDATE pacientes SET favorito = ? WHERE id = ?", (novo_status, paciente_id))
        conn.commit()
        conn.close()
        
        return jsonify({
            "status": "success", 
            "message": f"Status de favorito atualizado para {'favorito' if novo_status else 'não favorito'}"
        })
    
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"Erro ao atualizar favorito: {str(e)}")
        print(error_details)
        return jsonify({"status": "error", "message": str(e), "details": error_details}), 500

# Rota para servir o painel administrativo
@app.route('/admin')
def admin():
    return send_from_directory('.', 'admin.html')

# Rota para a página about
@app.route('/quiroabout')
def about():
    return send_from_directory('.', 'quiroabout.html')

# Rota para exportar dados CSV
@app.route('/api/exportar-csv', methods=['GET'])
def exportar_csv():
    try:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM pacientes ORDER BY timestamp DESC")
        pacientes = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        if not pacientes:
            return jsonify({"status": "error", "message": "Não há dados para exportar"}), 404
        
        # Criar conteúdo CSV
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=pacientes[0].keys())
        writer.writeheader()
        writer.writerows(pacientes)
        
        # Criar resposta com arquivo CSV
        from flask import Response
        response = Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment;filename=pacientes_quiropraxia.csv"}
        )
        
        return response

    
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"Erro ao exportar CSV: {str(e)}")
        print(error_details)
        return jsonify({"status": "error", "message": str(e), "details": error_details}), 500


if __name__ == "__main__":
    warnings.filterwarnings("ignore", category=Warning)  # Suprime o aviso
    app.run(debug=True, host='0.0.0.0')  # Habilitado modo debug para mensagens de erro mais detalhadas