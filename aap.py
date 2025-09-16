import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from io import BytesIO
import base64
import os
import hashlib
import time
import uuid

# Configuração da página para mobile
st.set_page_config(
    page_title="v.Ferreira - Sistema de Inquéritos",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="auto"
)

# CSS personalizado melhorado
st.markdown("""
    <style>
    /* Ajustes gerais para mobile */
    @media (max-width: 768px) {
        .main .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }
        
        h1 {
            font-size: 1.8rem !important;
        }
        
        h2 {
            font-size: 1.5rem !important;
        }
        
        h3 {
            font-size: 1.3rem !important;
        }
        
        /* Ajustar sliders para mobile */
        .stSlider {
            width: 100% !important;
        }
        
        /* Ajustar botões para mobile */
        .stButton > button {
            width: 100%;
            margin-bottom: 0.5rem;
        }
        
        /* Ajustar colunas para mobile */
        .stHorizontalBlock > div {
            flex-direction: column;
        }
        
        /* Ajustar tabelas para mobile */
        .dataframe {
            font-size: 0.8rem;
        }
        
        /* Melhorar formulários para mobile */
        .stForm {
            padding: 0.5rem;
        }
        
        /* Agrupar sliders por dimensão */
        .dimension-group {
            background-color: #f8f9fa;
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
            border-left: 4px solid #1E90FF;
        }
        
        /* Estilo para botões de seleção de formulário */
        .form-selector {
            text-align: center;
            padding: 1.5rem;
            margin: 1rem 0;
            border-radius: 10px;
            background-color: #f0f2f6;
            transition: all 0.3s ease;
        }
        
        .form-selector:hover {
            background-color: #e6e9ef;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
    }
    
    /* Cursor azul para os sliders */
    .stSlider > div > div > div > div {
        background-color: #1E90FF !important;
    }
    
    /* Melhorar a legibilidade dos textos */
    .stMarkdown {
        font-size: 1rem;
        line-height: 1.5;
    }
    
    /* Ajustar os formulários para mobile */
    .stForm {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 1rem;
    }
    
    /* Estilos para as métricas de desempenho */
    .good-performance {
        color: #27ae60;
        font-weight: bold;
    }
    .medium-performance {
        color: #f39c12;
        font-weight: bold;
    }
    .poor-performance {
        color: #e74c3c;
        font-weight: bold;
    }
    
    /* Melhorar visualização de comentários */
    .comment-box {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        border-left: 4px solid #6c757d;
    }
    </style>
""", unsafe_allow_html=True)

# Função para hash de senhas
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Função para migrar o banco de dados (versão melhorada)
def migrate_db():
    conn = sqlite3.connect('hpo_survey.db')
    c = conn.cursor()
    
    # Verificar se a coluna comentario já existe na tabela HPO
    c.execute("PRAGMA table_info(responses)")
    columns = [column[1] for column in c.fetchall()]
    
    if 'comentario' not in columns:
        # Adicionar a coluna comentario se não existir
        c.execute("ALTER TABLE responses ADD COLUMN comentario TEXT")
        print("Banco de dados atualizado com a coluna de comentários para HPO!")
    
    # Verificar se a tabela de liderança existe
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lideranca_responses'")
    table_exists = c.fetchone()
    
    if table_exists:
        # Verificar a estrutura atual da tabela
        c.execute("PRAGMA table_info(lideranca_responses)")
        columns = [column[1] for column in c.fetchall()]
        
        # Se a tabela tem a estrutura antiga (com colunas q1, q2, etc.)
        if 'q1' in columns:
            # Criar uma nova tabela com a estrutura desejada
            c.execute('''
                CREATE TABLE lideranca_responses_new (
                    id INTEGER PRIMARY KEY, 
                    session_id TEXT,
                    timestamp DATETIME,
                    question_id TEXT,
                    response TEXT,
                    response_time REAL
                )
            ''')
            
            # Inserir dados da tabela antiga na nova estrutura
            # Como não temos session_id e response_time, vamos usar valores padrão
            # E vamos transformar as colunas q1, q2, etc. em linhas
            for i in range(1, 7):
                c.execute(f"""
                    INSERT INTO lideranca_responses_new (session_id, timestamp, question_id, response, response_time)
                    SELECT 
                        'migrated_' || id, 
                        timestamp, 
                        'q{i}', 
                        q{i}, 
                        0.0 
                    FROM lideranca_responses 
                    WHERE q{i} IS NOT NULL
                """)
            
            # Remover a tabela antiga
            c.execute("DROP TABLE lideranca_responses")
            
            # Renomear a nova tabela
            c.execute("ALTER TABLE lideranca_responses_new RENAME TO lideranca_responses")
            
            print("Tabela de liderança migrada para a nova estrutura!")
        
        else:
            # A tabela existe mas não tem a estrutura antiga, verificar se tem as colunas necessárias
            required_columns = ['session_id', 'question_id', 'response', 'response_time']
            missing_columns = [col for col in required_columns if col not in columns]
            
            if missing_columns:
                # Adicionar colunas faltantes
                for col in missing_columns:
                    if col == 'session_id':
                        c.execute("ALTER TABLE lideranca_responses ADD COLUMN session_id TEXT")
                    elif col == 'question_id':
                        c.execute("ALTER TABLE lideranca_responses ADD COLUMN question_id TEXT")
                    elif col == 'response':
                        c.execute("ALTER TABLE lideranca_responses ADD COLUMN response TEXT")
                    elif col == 'response_time':
                        c.execute("ALTER TABLE lideranca_responses ADD COLUMN response_time REAL")
                
                print("Tabela de liderança atualizada com colunas faltantes!")
    
    else:
        # Criar tabela para respostas de liderança com a nova estrutura
        c.execute('''
            CREATE TABLE lideranca_responses (
                id INTEGER PRIMARY KEY, 
                session_id TEXT,
                timestamp DATETIME,
                question_id TEXT,
                response TEXT,
                response_time REAL
            )
        ''')
        print("Tabela de liderança criada com nova estrutura!")
    
    conn.commit()
    conn.close()

# Inicialização do banco de dados
def init_db():
    conn = sqlite3.connect('hpo_survey.db')
    c = conn.cursor()
    
    # Tabela de usuários
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, role TEXT)''')
    
    # Tabela de respostas HPO (atualizada com campo de comentários)
    c.execute('''CREATE TABLE IF NOT EXISTS responses
                 (id INTEGER PRIMARY KEY, 
                  timestamp DATETIME,
                  a1 INTEGER, a2 INTEGER,
                  b1 INTEGER, b2 INTEGER,
                  c1 INTEGER, c2 INTEGER,
                  d1 INTEGER, d2 INTEGER,
                  e1 INTEGER, e2 INTEGER,
                  f1 INTEGER, f2 INTEGER,
                  g1 INTEGER, g2 INTEGER,
                  comentario TEXT)''')
    
    # Tabela de respostas de Liderança
    c.execute('''CREATE TABLE IF NOT EXISTS lideranca_responses
                 (id INTEGER PRIMARY KEY, 
                  timestamp DATETIME,
                  q1 TEXT, q2 TEXT, q3 TEXT, 
                  q4 TEXT, q5 TEXT, q6 TEXT,
                  comentario TEXT)''')
    
    # Inserir usuários padrão se não existirem (com senhas hasheadas)
    default_users = [
        ('admin', hash_password('admin123'), 'administrador'),
        ('gestor', hash_password('gestor123'), 'gestor')
    ]
    
    for username, password, role in default_users:
        try:
            c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                     (username, password, role))
        except sqlite3.IntegrityError:
            pass  # Usuário já existe
    
    conn.commit()
    conn.close()
    
    # Migrar banco de dados existente
    migrate_db()

# Função para verificar login
def check_login(username, password):
    conn = sqlite3.connect('hpo_survey.db')
    c = conn.cursor()
    hashed_password = hash_password(password)
    c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, hashed_password))
    user = c.fetchone()
    conn.close()
    return user

# Função para adicionar novo usuário (apenas admin)
def add_user(username, password, role):
    conn = sqlite3.connect('hpo_survey.db')
    c = conn.cursor()
    hashed_password = hash_password(password)
    try:
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                 (username, hashed_password, role))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    conn.close()
    return success

# Função para listar usuários (apenas admin)
def list_users():
    conn = sqlite3.connect('hpo_survey.db')
    c = conn.cursor()
    c.execute("SELECT id, username, role FROM users")
    users = c.fetchall()
    conn.close()
    return users

# Função para excluir usuário (apenas admin)
def delete_user(user_id):
    conn = sqlite3.connect('hpo_survey.db')
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

# Função para editar usuário (apenas admin)
def edit_user(user_id, new_username=None, new_password=None, new_role=None):
    conn = sqlite3.connect('hpo_survey.db')
    c = conn.cursor()
    success = False
    
    try:
        # Verificar se o usuário existe
        c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = c.fetchone()
        
        if user:
            # Construir a query dinamicamente baseada nos campos fornecidos
            update_fields = []
            params = []
            
            if new_username is not None:
                update_fields.append("username = ?")
                params.append(new_username)
            
            if new_password is not None:
                update_fields.append("password = ?")
                params.append(hash_password(new_password))
            
            if new_role is not None:
                update_fields.append("role = ?")
                params.append(new_role)
            
            if update_fields:
                # Adicionar o user_id aos parâmetros
                params.append(user_id)
                
                # Executar a atualização
                query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = ?"
                c.execute(query, params)
                conn.commit()
                success = True
        
    except sqlite3.Error as e:
        print(f"Erro ao editar usuário: {e}")
        success = False
    
    finally:
        conn.close()
    
    return success

# Função para buscar informações de um usuário específico
def get_user(user_id):
    conn = sqlite3.connect('hpo_survey.db')
    c = conn.cursor()
    c.execute("SELECT id, username, role FROM users WHERE id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user   

# Função para resetar completamente o sistema (apenas admin)
def reset_entire_system():
    try:
        # Apagar todas as respostas
        delete_all_responses()
        
        # Limpar cache do Streamlit para forçar recálculo de todas as estatísticas
        st.cache_data.clear()
        
        # Recriar o banco de dados para garantir limpeza completa
        init_db()
        
        return True
    except Exception as e:
        st.error(f"Erro durante o reset: {str(e)}")
        return False

# Função para apagar todas as respostas (apenas admin)
def delete_all_responses():
    conn = sqlite3.connect('hpo_survey.db')
    c = conn.cursor()
    c.execute("DELETE FROM responses")
    c.execute("DELETE FROM lideranca_responses")
    conn.commit()
    conn.close()

# Função para salvar resposta do questionário HPO
def save_hpo_response(responses, comentario=""):
    conn = sqlite3.connect('hpo_survey.db')
    c = conn.cursor()
    
    c.execute('''INSERT INTO responses 
                 (timestamp, a1, a2, b1, b2, c1, c2, d1, d2, e1, e2, f1, f2, g1, g2, comentario)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                 (datetime.now(),) + tuple(responses) + (comentario,))
    
    conn.commit()
    conn.close()

# Função para salvar resposta do questionário de Liderança
def save_lideranca_response(session_id, question_data):
    conn = sqlite3.connect('hpo_survey.db')
    c = conn.cursor()
    
    # Inserir cada resposta individualmente
    for i, (question_id, response, response_time) in enumerate(question_data, 1):
        c.execute('''INSERT INTO lideranca_responses 
                     (session_id, timestamp, question_id, response, response_time)
                     VALUES (?, ?, ?, ?, ?)''',
                     (session_id, datetime.now(), f"q{i}", response, response_time))
    
    conn.commit()
    conn.close()

# Função para carregar todas as respostas HPO
def load_hpo_responses():
    conn = sqlite3.connect('hpo_survey.db')
    
    # Verificar se a coluna comentario existe
    c = conn.cursor()
    c.execute("PRAGMA table_info(responses)")
    columns = [column[1] for column in c.fetchall()]
    
    if 'comentario' not in columns:
        # Se a coluna não existir, criar uma coluna dummy
        df = pd.read_sql_query("SELECT * FROM responses", conn)
        df['comentario'] = ''  # Adicionar coluna vazia
    else:
        df = pd.read_sql_query("SELECT * FROM responses", conn)
    
    conn.close()
    return df

# Função para carregar todas as respostas de Liderança (modificada)
def load_lideranca_responses():
    conn = sqlite3.connect('hpo_survey.db')
    df = pd.read_sql_query("SELECT * FROM lideranca_responses", conn)
    conn.close()
    return df

# Função para calcular estatísticas HPO
def calculate_hpo_stats(df):
    if df.empty:
        return None, None, None, None
    
    # Calcular totais por dimensão (soma das duas questões, máximo de 14 pontos)
    dimensions = {
        'A. Informação partilhada e comunicação aberta': ['a1', 'a2'],
        'B. Visão forte: objetivo e valores': ['b1', 'b2'],
        'C. Aprendizagem contínua': ['c1', 'c2'],
        'D. Focalização constante nos resultados dos clientes': ['d1', 'd2'],
        'E. Sistemas e estruturas enérgicos': ['e1', 'e2'],
        'F. Poder partilhado e envolvimento elevado': ['f1', 'f2'],
        'G. Liderança': ['g1', 'g2']
    }
    
    # Calcular totais por dimensão para cada resposta
    dimension_totals = {}
    for dim, cols in dimensions.items():
        dimension_totals[dim] = df[cols].sum(axis=1)
    
    # Calcular médias dos totais por dimensão
    stats = {}
    for dim, totals in dimension_totals.items():
        stats[dim] = totals.mean()
    
    # Classificar o desempenho por dimensão
    performance = {}
    for dim, avg_total in stats.items():
        if avg_total >= 12:
            performance[dim] = "Elevado desempenho"
        elif avg_total >= 9:
            performance[dim] = "Médio"
        else:
            performance[dim] = "Oportunidade de melhoria"
    
    # Calcular desempenho geral da organização
    overall_avg = sum(stats.values()) / len(stats)
    if overall_avg >= 12:
        overall_performance = "Elevado desempenho"
    elif overall_avg >= 9:
        overall_performance = "Médio"
    else:
        overall_performance = "Oportunidade de melhoria"
    
    return stats, performance, overall_performance, dimension_totals

# Função para calcular estatísticas de Liderança (modificada)
def calculate_lideranca_stats(df):
    if df.empty:
        return None, None
    
    # Respostas corretas (baseadas no documento)
    correct_answers = {
        'q1': 'b',
        'q2': 'a',
        'q3': 'a',
        'q4': 'b',
        'q5': 'a',
        'q6': 'b'
    }
    
    # Calcular pontuação por questão
    question_stats = {}
    for q, correct in correct_answers.items():
        question_df = df[df['question_id'] == q]
        if not question_df.empty:
            correct_count = (question_df['response'] == correct).sum()
            total_count = question_df['response'].count()
            accuracy = (correct_count / total_count * 100) if total_count > 0 else 0
            
            # Calcular tempo médio de resposta
            avg_time = question_df['response_time'].mean()
            
            question_stats[q] = {
                'corretas': correct_count,
                'total': total_count,
                'acuracia': accuracy,
                'tempo_medio': avg_time
            }
    
    # Calcular pontuação geral
    total_correct = sum(stats['corretas'] for stats in question_stats.values())
    total_questions = sum(stats['total'] for stats in question_stats.values()) if question_stats else 0
    overall_accuracy = (total_correct / (total_questions / 6) * 100) if total_questions > 0 else 0
    
    return question_stats, overall_accuracy

# Função para criar visualização de dados HPO nativa do Streamlit
def display_hpo_stats(stats, performance):
    # Criar DataFrame para exibição
    stats_df = pd.DataFrame({
        'Dimensão': list(stats.keys()),
        'Pontuação Média': [f"{v:.2f}/14" for v in stats.values()],
        'Desempenho': list(performance.values())
    })
    
    # Exibir tabela com formatação condicional
    for idx, row in stats_df.iterrows():
        col1, col2, col3 = st.columns([4, 2, 2])
        with col1:
            st.write(f"**{row['Dimensão']}**")
        with col2:
            st.write(row['Pontuação Média'])
        with col3:
            if row['Desempenho'] == "Elevado desempenho":
                st.markdown(f'<span class="good-performance">{row["Desempenho"]}</span>', unsafe_allow_html=True)
            elif row['Desempenho'] == "Médio":
                st.markdown(f'<span class="medium-performance">{row["Desempenho"]}</span>', unsafe_allow_html=True)
            else:
                st.markdown(f'<span class="poor-performance">{row["Desempenho"]}</span>', unsafe_allow_html=True)
    
    return stats_df

# Função para criar visualização de dados de Liderança (modificada)
def display_lideranca_stats(question_stats, overall_accuracy):
    st.metric("Pontuação Geral", f"{overall_accuracy:.1f}%")
    
    # Definir textos das questões
    question_texts = {
        'q1': "1. Liderar a um nível superior significa:",
        'q2': "2. Valores da Liderança:",
        'q3': "3. Os Três Resultados de uma organização com elevado desempenho são:",
        'q4': "4. A chave para delegação de poderes é:",
        'q5': "5. Os quatro estilos básicos de liderança no modelo de Liderança Situacional são:",
        'q6': "6. Comportamentos de apoio em Equipa são:"
    }
    
    # Exibir estatísticas por questão
    for q, stats in question_stats.items():
        with st.expander(question_texts.get(q, q)):
            st.write(f"Respostas corretas: {stats['corretas']}/{stats['total']}")
            st.write(f"Taxa de acerto: {stats['acuracia']:.1f}%")
            st.write(f"Tempo médio de resposta: {stats['tempo_medio']:.1f} segundos")
            st.progress(stats['acuracia'] / 100)

# Função para criar gráfico de barras HPO usando native Streamlit chart
def create_hpo_chart(stats):
    chart_data = pd.DataFrame({
        'Dimensão': list(stats.keys()),
        'Pontuação Média': list(stats.values())
    })
    
    st.bar_chart(chart_data.set_index('Dimensão'), height=400)

# Função para mostrar distribuição de respostas HPO
def show_hpo_distribution(df):
    # Remover colunas não numéricas
    numeric_columns = [col for col in df.columns if col not in ['id', 'timestamp', 'comentario']]
    all_responses = df[numeric_columns].values.flatten()
    
    # Criar DataFrame para o gráfico
    dist_data = pd.Series(all_responses).value_counts().sort_index()
    dist_df = pd.DataFrame({
        'Pontuação': dist_data.index,
        'Frequência': dist_data.values
    })
    
    st.bar_chart(dist_df.set_index('Pontuação'), height=300)

# Função para gerar relatório HPO em HTML simplificado
def generate_hpo_html_report(stats, performance, overall_performance, df):
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Relatório HPO - Análise de Desempenho</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1 {{ color: #2c3e50; font-size: 1.8rem; }}
            h2 {{ color: #34495e; border-bottom: 2px solid #3498db; padding-bottom: 5px; font-size: 1.5rem; }}
            table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; font-size: 0.9rem; }}
            th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
            th {{ background-color: #3498db; color: white; }}
            tr:nth-child(even) {{ background-color: #f2f2f2; }}
            .summary-item {{ margin: 10px 0; }}
            .good {{ color: #27ae60; }}
            .medium {{ color: #f39c12; }}
            .poor {{ color: #e74c3c; }}
            .info {{ background-color: #e8f4fc; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            .comentario {{ background-color: #f9f9f9; padding: 15px; border-left: 4px solid #3498db; margin: 10px 0; }}
            @media (max-width: 768px) {{
                body {{ margin: 10px; }}
                h1 {{ font-size: 1.5rem; }}
                h2 {{ font-size: 1.3rem; }}
                table {{ font-size: 0.8rem; }}
                th, td {{ padding: 8px; }}
            }}
        </style>
    </head>
    <body>
        <h1>Relatório HPO - Análise de Desempenho</h1>
        <p><strong>Gerado em:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
        
        <div class="info">
            <h2>Desempenho Geral</h2>
            <h3>{overall_performance}</h3>
        </div>
        
        <h2>Resultados por Dimensão</h2>
        <table>
            <tr>
                <th>Dimensão</th>
                <th>Pontuação Média</th>
                <th>Desempenho</th>
            </tr>
    """
    
    for dim, avg_total in stats.items():
        perf_class = ""
        if performance[dim] == "Elevado desempenho":
            perf_class = "good"
        elif performance[dim] == "Médio":
            perf_class = "medium"
        else:
            perf_class = "poor"
            
        html_content += f"""
            <tr>
                <td>{dim}</td>
                <td>{avg_total:.2f}/14</td>
                <td class="{perf_class}">{performance[dim]}</td>
            </tr>
        """
    
    html_content += """
        </table>
        
        <h2>Resumo Executivo</h2>
    """
    
    for dim, perf in performance.items():
        emoji = "✅" if perf == "Elevado desempenho" else "⚠️" if perf == "Médio" else "❌"
        perf_class = "good" if perf == "Elevado desempenho" else "medium" if perf == "Médio" else "poor"
        
        html_content += f"""
        <div class="summary-item {perf_class}">
            {emoji} <strong>{dim}</strong>: {perf}
        </div>
        """
    
    # Comentários dos participantes (se houver)
    if 'comentario' in df.columns:
        comentarios_df = df[df['comentario'].notna() & (df['comentario'] != '')]
        if not comentarios_df.empty:
            html_content += """
            <h2>Comentários dos Participantes</h2>
            """
            
            for idx, row in comentarios_df.iterrows():
                html_content += f"""
                <div class="comentario">
                    <strong>{row['timestamp']}:</strong><br>
                    {row['comentario']}
                </div>
                """
    
    html_content += f"""
        <h2>Informações Adicionais</h2>
        <p><strong>Total de respostas:</strong> {len(df)}</p>
    """
    
    if 'comentario' in df.columns:
        comentarios_df = df[df['comentario'].notna() & (df['comentario'] != '')]
        html_content += f"""
        <p><strong>Total de comentários:</strong> {len(comentarios_df)}</p>
        """
    
    html_content += f"""
        <p><strong>Período das respostas:</strong> {df['timestamp'].min()} a {df['timestamp'].max()}</p>
    </body>
    </html>
    """
    
    return html_content.encode('utf-8')

# Função para gerar relatório de Liderança em HTML (modificada)
def generate_lideranca_html_report(question_stats, overall_accuracy, df):
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Relatório de Liderança - Análise de Desempenho</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1 {{ color: #2c3e50; font-size: 1.8rem; }}
            h2 {{ color: #34495e; border-bottom: 2px solid #3498db; padding-bottom: 5px; font-size: 1.5rem; }}
            table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; font-size: 0.9rem; }}
            th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
            th {{ background-color: #3498db; color: white; }}
            tr:nth-child(even) {{ background-color: #f2f2f2; }}
            .summary-item {{ margin: 10px 0; }}
            .good {{ color: #27ae60; }}
            .medium {{ color: #f39c12; }}
            .poor {{ color: #e74c3c; }}
            .info {{ background-color: #e8f4fc; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            @media (max-width: 768px) {{
                body {{ margin: 10px; }}
                h1 {{ font-size: 1.5rem; }}
                h2 {{ font-size: 1.3rem; }}
                table {{ font-size: 0.8rem; }}
                th, td {{ padding: 8px; }}
            }}
        </style>
    </head>
    <body>
        <h1>Relatório de Liderança - Análise de Desempenho</h1>
        <p><strong>Gerado em:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
        
        <div class="info">
            <h2>Desempenho Geral</h2>
            <h3>{overall_accuracy:.1f}% de acerto</h3>
        </div>
        
        <h2>Resultados por Questão</h2>
        <table>
            <tr>
                <th>Questão</th>
                <th>Respostas Corretas</th>
                <th>Taxa de Acerto</th>
                <th>Tempo Médio (segundos)</th>
            </tr>
    """
    
    # Definir textos das questões
    question_texts = {
        'q1': "1. Liderar a um nível superior significa:",
        'q2': "2. Valores da Liderança:",
        'q3': "3. Os Três Resultados de uma organização com elevado desempenho são:",
        'q4': "4. A chave para delegação de poderes é:",
        'q5': "5. Os quatro estilos básicos de liderança no modelo de Liderança Situacional são:",
        'q6': "6. Comportamentos de apoio em Equipa são:"
    }
    
    for q, stats in question_stats.items():
        html_content += f"""
            <tr>
                <td>{question_texts.get(q, q)}</td>
                <td>{stats['corretas']}/{stats['total']}</td>
                <td>{stats['acuracia']:.1f}%</td>
                <td>{stats['tempo_medio']:.1f}</td>
            </tr>
        """
    
    html_content += """
        </table>
    """
    
    html_content += f"""
        <h2>Informações Adicionais</h2>
        <p><strong>Total de sessões completadas:</strong> {df['session_id'].nunique()}</p>
        <p><strong>Total de respostas:</strong> {len(df)}</p>
        <p><strong>Período das respostas:</strong> {df['timestamp'].min()} a {df['timestamp'].max()}</p>
    </body>
    </html>
    """
    
    return html_content.encode('utf-8')

# Página de login
def login_page():
    st.title("📊 EPEC - Sistema de Inquéritos")
    st.subheader("Login")
    
    # Opção para trabalhador
    if st.button("Sou Trabalhador (Clicar)", use_container_width=True):
        st.session_state.logged_in = True
        st.session_state.role = "trabalhador"
        st.session_state.form_type = None  # Resetar seleção de formulário
        st.rerun()
    
    # Formulário de login para admin/gestor
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login", use_container_width=True)
        
        if submitted:
            user = check_login(username, password)
            if user:
                st.session_state.logged_in = True
                st.session_state.user_id = user[0]
                st.session_state.username = user[1]
                st.session_state.role = user[3]
                st.rerun()
            else:
                st.error("Username ou password incorretos")

# Página de seleção de formulário para trabalhador
def form_selection_page():
    st.title("EPEC - Seleção de Questionário")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="form-selector">', unsafe_allow_html=True)
        st.subheader("Questionário HPO")
        st.write("Avaliação das práticas de alta performance organizacional")
        if st.button("Selecionar HPO", key="hpo_btn", use_container_width=True):
            st.session_state.form_type = "hpo"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="form-selector">', unsafe_allow_html=True)
        st.subheader("Questionário de Liderança")
        st.write("Avaliação de conhecimentos sobre liderança")
        if st.button("Selecionar Liderança", key="lideranca_btn", use_container_width=True):
            st.session_state.form_type = "lideranca"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# Página do questionário HPO para trabalhador
def survey_hpo_page():
    st.title("EPEC - Questionário HPO")    
    st.info("""
     **Escala de 1 a 7: **
     - 1 - Discordo Totalmente
     - 2 - Discordo
     - 3 - Discordo Pouco
     - 4 - Neutro
     - 5 - Concordo Pouco
     - 6 - Concordo
     - 7 - Concordo Totalmente
     """)

    st.write("Por favor, responda às seguintes questões com base na sua experiência na organização.")
    st.info("Nota: Cada dimensão recebe uma pontuação total de até 14 pontos (7 pontos por questão).")
    
    # Verificar se já foi submetido para mostrar mensagem de confirmação
    if 'submitted' in st.session_state and st.session_state.submitted:
        st.success("""
        ✅ **Questionário submetido com sucesso!**
        
        Obrigado pela sua participação. A sua opinião é muito importante para nós.
        """)
        
        # Botão para preencher novo questionário
        if st.button("Preencher novo questionário"):
            st.session_state.submitted = False
            st.session_state.form_type = None
            st.rerun()
            
        return
    
    with st.form("survey_form"):
        # Agrupar questões por dimensão para melhor organização
        dimensions = [
            {
                "title": "A. Informação partilhada e comunicação aberta",
                "questions": [
                    "1. Os colaboradores têm facilmente acesso à informação de que necessitam para realizar o seu trabalho com eficácia.",
                    "2. Os planos e decisões são comunicados de forma a serem claramente compreendidos."
                ]
            },
            {
                "title": "B. Visão forte: objetivo e valores",
                "questions": [
                    "1. Na sua organização, a liderança está alinhada com uma visão e valores partilhados.",
                    "2. Na sua organização, os colaboradores têm paixão por um objetivo e valores partilhados."
                ]
            },
            {
                "title": "C. Aprendizagem contínua",
                "questions": [
                    "1. Na sua organização, os colaboradores são apoiados ativamente no desenvolvimento de novas capacidades e competências.",
                    "2. A sua organização incorpora continuamente novas aprendizagens no modo habitual de fazer negócios."
                ]
            },
            {
                "title": "D. Focalização constante nos resultados dos clientes",
                "questions": [
                    "1. Todos na sua organização mantêm os mais elevados critérios de qualidade e serviço.",
                    "2. Todos os processos de trabalho são elaborados de forma a facilitar aos seus clientes fazer negócios consigo."
                ]
            },
            {
                "title": "E. Sistemas e estruturas enérgicos",
                "questions": [
                    "1. Os sistemas, estruturas e práticas formais e informais estão integrados e alinhados uns com os outros.",
                    "2. Na sua organização, os sistemas, estruturas e práticas formais e informais facilitar os colaboradores a realização do seu trabalho."
                ]
            },
            {
                "title": "F. Poder partilhado e envolvimento elevado",
                "questions": [
                    "1. Todos têm a oportunidade de influenciar as decisões que os afetam.",
                    "2. As equipas são utilizadas como um veículo para a realização de trabalho e influenciar decisões."
                ]
            },
            {
                "title": "G. Liderança",
                "questions": [
                    "1. Os Líderes acreditam que liderar é servir e não ser servido.",
                    "2. Os líderes removem obstáculos de forma a ajudar os colaboradores a concentraren-se no seu trabalho e nos seus clientes."
                ]
            }
        ]
        
        responses = []
        for i, dimension in enumerate(dimensions):
            st.markdown(f'<div class="dimension-group">', unsafe_allow_html=True)
            st.subheader(dimension["title"])
            
            for j, question in enumerate(dimension["questions"]):
                # Usar uma chave única para cada slider
                key = f"{chr(97+i)}{j+1}"
                value = st.slider(question, 1, 7, 4, key=key)
                responses.append(value)
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Campo de comentário
        st.subheader("Comentários Adicionais")
        comentario = st.text_area("Tem algum comentário ou sugestão adicional que gostaria de partilhar? (opcional)", 
                                 height=100, 
                                 placeholder="Partilhe aqui os seus pensamentos, sugestões ou observações adicionais...",
                                 key="comentario")
        
        submitted = st.form_submit_button("Submeter Questionário", use_container_width=True)
        
        if submitted:
            save_hpo_response(responses, comentario)
            st.session_state.submitted = True
            st.rerun()

# Página do questionário de Liderança para trabalhador (modificada)
def survey_lideranca_page():
    st.title("EPEC - Questionário de Liderança")
    st.info("""
    **Instruções:**
    Para cada questão, selecione a opção que considera correta.
    O tempo de resposta para cada pergunta será registrado.
    """)
    
    # Inicializar estado da sessão se não existir
    if 'lideranca_session_id' not in st.session_state:
        st.session_state.lideranca_session_id = str(uuid.uuid4())
        st.session_state.lideranca_current_question = 0
        st.session_state.lideranca_responses = []
        st.session_state.lideranca_start_time = time.time()
        st.session_state.lideranca_completed = False
    
    # Verificar se já foi concluído
    if st.session_state.lideranca_completed:
        st.success("""
        ✅ **Questionário concluído com sucesso!**
        
        Obrigado pela sua participação. A sua opinião é muito importante para nós.
        """)
        
        # Botão para preencher novo questionário
        if st.button("Preencher novo questionário"):
            st.session_state.lideranca_session_id = str(uuid.uuid4())
            st.session_state.lideranca_current_question = 0
            st.session_state.lideranca_responses = []
            st.session_state.lideranca_start_time = time.time()
            st.session_state.lideranca_completed = False
            st.session_state.form_type = None
            st.rerun()
            
        return
    
    # Definir perguntas
    questions = [
        {
            "question": "1. Liderar a um nível superior significa:",
            "options": [
                "a. Agir em proveito de si próprio",
                "b. Agir em proveito dos outros"
            ]
        },
        {
            "question": "2. Valores da Liderança:",
            "options": [
                "a. Ética, Relações, Sucesso e Aprendizagem",
                "b. Ética, Autoridade, Dinheiro e Padrão"
            ]
        },
        {
            "question": "3. Os Três Resultados de uma organização com elevado desempenho são:",
            "options": [
                "a. Fornecedor preferencial, empregador preferencial e Investimento preferencial",
                "b. Fornecedor preferencial, empregador preferencial e Investigador preferencial"
            ]
        },
        {
            "question": "4. A chave para delegação de poderes é:",
            "options": [
                "a. Ter mais poder",
                "b. Libertar esse poder"
            ]
        },
        {
            "question": "5. Os quatro estilos básicos de liderança no modelo de Liderança Situacional são:",
            "options": [
                "a. Direção, Coaching, Apoio e Delegação",
                "b. Direção, Coaching, Apoio e Autoridade"
            ]
        },
        {
            "question": "6. Comportamentos de apoio em Equipa são:",
            "options": [
                "a. Organizar, educar, centrar e estruturar",
                "b. Elogiar, envolver, ouvir e encorajar"
            ]
        }
    ]
    
    # Obter pergunta atual
    current_question_idx = st.session_state.lideranca_current_question
    current_question = questions[current_question_idx]
    
    # Exibir progresso
    st.progress((current_question_idx + 1) / len(questions))
    st.write(f"Pergunta {current_question_idx + 1} de {len(questions)}")
    
    # Exibir pergunta atual
    st.subheader(current_question["question"])
    
    # Formulário para resposta atual
    with st.form(f"question_{current_question_idx}"):
        response = st.radio(
            "Selecione a opção correta:",
            options=["a", "b"],
            format_func=lambda x: next(opt for opt in current_question["options"] if opt.startswith(x)),
            key=f"q{current_question_idx}",
            index=None
        )
        
        submitted = st.form_submit_button("Submeter Resposta", use_container_width=True)
        
        if submitted:
            if response is None:
                st.error("Por favor, selecione uma opção antes de submeter.")
            else:
                # Calcular tempo de resposta
                response_time = time.time() - st.session_state.lideranca_start_time
                
                # Armazenar resposta
                st.session_state.lideranca_responses.append(
                    (f"q{current_question_idx + 1}", response, response_time)
                )
                
                # Verificar se é a última pergunta
                if current_question_idx + 1 >= len(questions):
                    # Salvar todas as respostas
                    save_lideranca_response(
                        st.session_state.lideranca_session_id,
                        st.session_state.lideranca_responses
                    )
                    st.session_state.lideranca_completed = True
                else:
                    # Preparar próxima pergunta
                    st.session_state.lideranca_current_question += 1
                    st.session_state.lideranca_start_time = time.time()
                
                st.rerun()

# Página de gestão para gestores
def manager_page():
    st.title("Painel de Gestão")
    
    tab1, tab2, tab3 = st.tabs(["Estatísticas HPO", "Estatísticas Liderança", "Relatórios"])
    
    with tab1:
        st.subheader("Estatísticas das Respostas - Protocolo HPO")
        st.info("""
        **Protocolo de Pontuação:**
        - Pontuação 12 - 14 = Elevado desempenho
        - Pontuação 9 - 11 = Médio
        - Pontuação igual ou inferior a 8 = Oportunidade de melhoria
        """)
        
        df = load_hpo_responses()
        
        if not df.empty:
            stats, performance, overall_performance, _ = calculate_hpo_stats(df)
            
            # Gráfico de barras nativo do Streamlit
            st.subheader("Desempenho por Dimensão")
            create_hpo_chart(stats)
            
            # Tabela de pontuações e desempenho
            st.subheader("Pontuações e Desempenho por Dimensão")
            display_hpo_stats(stats, performance)
            
            # Desempenho geral
            st.subheader("Desempenho Geral da Organização")
            st.metric("Classificação Geral", overall_performance)
            
            # Distribuição das respostas
            st.subheader("Distribuição das Respostas Individuais")
            show_hpo_distribution(df)
            
            # Comentários
            if 'comentario' in df.columns:
                comentarios_df = df[df['comentario'].notna() & (df['comentario'] != '')]
                if not comentarios_df.empty:
                    st.subheader("Comentários dos Participantes")
                    for idx, row in comentarios_df.iterrows():
                        with st.expander(f"Comentário de {row['timestamp']}"):
                            st.markdown(f'<div class="comment-box">{row["comentario"]}</div>', unsafe_allow_html=True)
            else:
                st.info("Coluna de comentários não disponível no banco de dados.")
            
        else:
            st.info("Ainda não existem respostas HPO para analisar.")
    
    with tab2:
        st.subheader("Estatísticas das Respostas - Questionário de Liderança")
        
        df = load_lideranca_responses()
        
        if not df.empty:
            question_stats, overall_accuracy = calculate_lideranca_stats(df)
            
            st.subheader("Desempenho Geral")
            display_lideranca_stats(question_stats, overall_accuracy)
            
            # Comentários
            if 'comentario' in df.columns:
                comentarios_df = df[df['comentario'].notna() & (df['comentario'] != '')]
                if not comentarios_df.empty:
                    st.subheader("Comentários dos Participantes")
                    for idx, row in comentarios_df.iterrows():
                        with st.expander(f"Comentário de {row['timestamp']}"):
                            st.markdown(f'<div class="comment-box">{row["comentario"]}</div>', unsafe_allow_html=True)
            
        else:
            st.info("Ainda não existem respostas de Liderança para analisar.")
    
    with tab3:
        st.subheader("Relatórios de Análise")
        
        report_type = st.radio("Selecione o tipo de relatório:", 
                              ["HPO", "Liderança"],
                              horizontal=True)
        
        if report_type == "HPO":
            df = load_hpo_responses()
            
            if not df.empty:
                stats, performance, overall_performance, _ = calculate_hpo_stats(df)
                
                st.info("Gere relatórios detalhados com a análise completa dos dados do inquérito HPO.")
                
                st.subheader("Relatório em HTML")
                st.write("Relatório completo em formato HTML para visualização no navegador.")
                
                html_report = generate_hpo_html_report(stats, performance, overall_performance, df)
                
                st.download_button(
                    label="Descarregar Relatório HPO",
                    data=html_report,
                    file_name="relatorio_hpo.html",
                    mime="text/html",
                    use_container_width=True
                )
                
                # Visualização prévia do relatório
                st.subheader("Pré-visualização do Relatório")
                with st.expander("Clique para ver a pré-visualização do relatório"):
                    # Mostrar uma versão simplificada do relatório
                    st.markdown(f"### Relatório HPO - Análise de Desempenho")
                    st.markdown(f"**Gerado em:** {datetime.now().strftime('%d/%m/%Y %H:%M')}")
                    st.markdown(f"**Total de respostas:** {len(df)}")
                    
                    if 'comentario' in df.columns:
                        comentarios_df = df[df['comentario'].notna() & (df['comentario'] != '')]
                        st.markdown(f"**Total de comentários:** {len(comentarios_df)}")
                    
                    st.markdown("#### Desempenho Geral")
                    st.markdown(f"**{overall_performance}**")
                    
                    st.markdown("#### Resultados por Dimensão")
                    for dim, avg_total in stats.items():
                        perf_class = ""
                        if performance[dim] == "Elevado desempenho":
                            perf_class = "good-performance"
                        elif performance[dim] == "Médio":
                            perf_class = "medium-performance"
                        else:
                            perf_class = "poor-performance"
                        
                        st.markdown(f"- **{dim}**: {avg_total:.2f}/14 - <span class='{perf_class}'>{performance[dim]}</span>", unsafe_allow_html=True)
            
            else:
                st.info("Ainda não existem respostas HPO para gerar relatórios.")
        
        else:  # Liderança
            df = load_lideranca_responses()
            
            if not df.empty:
                question_stats, overall_accuracy = calculate_lideranca_stats(df)
                
                st.info("Gere relatórios detalhados com a análise completa dos dados do inquérito de Liderança.")
                
                st.subheader("Relatório em HTML")
                st.write("Relatório completo em formato HTML para visualização no navegador.")
                
                html_report = generate_lideranca_html_report(question_stats, overall_accuracy, df)
                
                st.download_button(
                    label="Descarregar Relatório de Liderança",
                    data=html_report,
                    file_name="relatorio_lideranca.html",
                    mime="text/html",
                    use_container_width=True
                )
                
                # Visualização prévia do relatório
                st.subheader("Pré-visualização do Relatório")
                with st.expander("Clique para ver a pré-visualização do relatório"):
                    # Mostrar uma versão simplificada do relatório
                    st.markdown(f"### Relatório de Liderança - Análise de Desempenho")
                    st.markdown(f"**Gerado em:** {datetime.now().strftime('%d/%m/%Y %H:%M')}")
                    st.markdown(f"**Total de respostas:** {len(df)}")
                    
                    if 'comentario' in df.columns:
                        comentarios_df = df[df['comentario'].notna() & (df['comentario'] != '')]
                        st.markdown(f"**Total de comentários:** {len(comentarios_df)}")
                    
                    st.markdown("#### Desempenho Geral")
                    st.markdown(f"**{overall_accuracy:.1f}% de acerto**")
                    
                    st.markdown("#### Resultados por Questão")
                    for q, stats in question_stats.items():
                        st.markdown(f"- **Questão {q}**: {stats['corretas']}/{stats['total']} ({stats['acuracia']:.1f}%)")
            
            else:
                st.info("Ainda não existem respostas de Liderança para gerar relatórios.")

# Página de administração
def admin_page():
    st.title("Painel de Administração")
    
    # Inicializar estados da sessão se não existirem
    if 'refresh_needed' not in st.session_state:
        st.session_state.refresh_needed = False
    if 'user_to_delete' not in st.session_state:
        st.session_state.user_to_delete = None
    if 'editing_users' not in st.session_state:
        st.session_state.editing_users = {}
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Gestão de Utilizadores", "Estatísticas HPO", "Estatísticas Liderança", "Relatórios", "Manutenção"])
    
    with tab1:
        st.subheader("Gestão de Utilizadores")
        
        # Adicionar novo usuário
        with st.expander("Adicionar Novo Utilizador"):
            with st.form("add_user_form"):
                new_username = st.text_input("Username")
                new_password = st.text_input("Password", type="password")
                confirm_password = st.text_input("Confirmar Password", type="password")
                new_role = st.selectbox("Tipo de Utilizador", ["administrador", "gestor"])
                submitted = st.form_submit_button("Adicionar Utilizador", use_container_width=True)
                
                if submitted:
                    if new_password != confirm_password:
                        st.error("As passwords não coincidem!")
                    elif add_user(new_username, new_password, new_role):
                        st.success("Utilizador adicionado com sucesso!")
                        st.session_state.refresh_needed = True
                    else:
                        st.error("Erro ao adicionar utilizador. O username pode já existir.")
        
        # Listar e gerir usuários
        st.subheader("Utilizadores Existentes")
        users = list_users()
        
        if users:
            for user in users:
                user_id, username, role = user
                
                # Verificar se este usuário está sendo editado
                editing = st.session_state.editing_users.get(user_id, False)
                
                if editing:
                    # Modo de edição
                    with st.form(key=f"edit_form_{user_id}"):
                        col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
                        
                        with col1:
                            new_username = st.text_input("Username", value=username, key=f"username_{user_id}")
                        with col2:
                            new_role = st.selectbox(
                                "Tipo de Utilizador", 
                                ["administrador", "gestor"], 
                                index=0 if role == "administrador" else 1,
                                key=f"role_{user_id}"
                            )
                        with col3:
                            # Checkbox para alterar senha
                            change_password = st.checkbox("Alterar senha", key=f"change_pw_{user_id}")
                        with col4:
                            col4_1, col4_2 = st.columns(2)
                            with col4_1:
                                save_button = st.form_submit_button("💾", use_container_width=True, help="Guardar alterações")
                            with col4_2:
                                cancel_button = st.form_submit_button("❌", use_container_width=True, help="Cancelar edição")
                        
                        # Campos de senha (apenas mostrados se change_password estiver selecionado)
                        if change_password:
                            col_pw1, col_pw2, col_pw3 = st.columns(3)
                            with col_pw1:
                                current_password = st.text_input("Senha Atual", type="password", key=f"current_pw_{user_id}")
                            with col_pw2:
                                new_password = st.text_input("Nova Senha", type="password", key=f"new_pw_{user_id}")
                            with col_pw3:
                                confirm_new_password = st.text_input("Confirmar Nova Senha", type="password", key=f"confirm_pw_{user_id}")
                        
                        # Processar ações do formulário
                        if save_button:
                            # Validar se está a alterar a senha
                            password_valid = True
                            password_to_update = None
                            
                            if change_password:
                                # Verificar se a senha atual está correta
                                if not check_login(username, current_password):
                                    st.error("Senha atual incorreta!")
                                    password_valid = False
                                elif new_password != confirm_new_password:
                                    st.error("As novas passwords não coincidem!")
                                    password_valid = False
                                elif not new_password:
                                    st.error("A nova senha não pode estar vazia!")
                                    password_valid = False
                                else:
                                    password_to_update = new_password
                            
                            if password_valid:
                                # Preparar parâmetros para edição
                                if edit_user(user_id, new_username, password_to_update, new_role):
                                    st.success("Utilizador atualizado com sucesso!")
                                    st.session_state.editing_users[user_id] = False
                                    st.session_state.refresh_needed = True
                                else:
                                    st.error("Erro ao atualizar utilizador.")
                        
                        if cancel_button:
                            st.session_state.editing_users[user_id] = False
                            st.session_state.refresh_needed = True
                
                else:
                    # Modo de visualização normal
                    col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
                    with col1:
                        st.write(f"**{username}**")
                    with col2:
                        st.write(role)
                    with col3:
                        if st.button("✏️", key=f"edit_{user_id}", use_container_width=True, help="Editar utilizador"):
                            st.session_state.editing_users[user_id] = True
                            st.session_state.refresh_needed = True
                    with col4:
                        if st.button("🗑️", key=f"delete_{user_id}", use_container_width=True, help="Eliminar utilizador"):
                            st.session_state.user_to_delete = user_id
                            st.session_state.refresh_needed = True
                
                st.markdown("---")
            
            # Processar eliminação de usuário
            if st.session_state.user_to_delete is not None:
                user_id = st.session_state.user_to_delete
                delete_user(user_id)
                st.success(f"Utilizador eliminado com sucesso!")
                st.session_state.user_to_delete = None
                st.session_state.refresh_needed = True
            
        else:
            st.info("Não existem utilizadores registados.")
        
        # Atualizar a página se necessário
        if st.session_state.refresh_needed:
            st.session_state.refresh_needed = False
            st.rerun()
    
    with tab2:
        st.subheader("Estatísticas das Respostas - Protocolo HPO")
        st.info("""
        **Protocolo de Pontuação:**
        - Pontuação 12 - 14 = Elevado desempenho
        - Pontuação 9 - 11 = Médio
        - Pontuação igual ou inferior a 8 = Oportunidade de melhoria
        """)
        
        df = load_hpo_responses()
        
        if not df.empty:
            stats, performance, overall_performance, _ = calculate_hpo_stats(df)
            
            # Gráfico de barras nativo do Streamlit
            st.subheader("Desempenho por Dimensão")
            create_hpo_chart(stats)
            
            # Tabela de pontuações e desempenho
            st.subheader("Pontuações e Desempenho por Dimensão")
            display_hpo_stats(stats, performance)
            
            # Desempenho geral
            st.subheader("Desempenho Geral da Organização")
            st.metric("Classificação Geral", overall_performance)
            
            # Distribuição das respostas
            st.subheader("Distribuição das Respostas Individuais")
            show_hpo_distribution(df)
            
            # Comentários
            if 'comentario' in df.columns:
                comentarios_df = df[df['comentario'].notna() & (df['comentario'] != '')]
                if not comentarios_df.empty:
                    st.subheader("Comentários dos Participantes")
                    for idx, row in comentarios_df.iterrows():
                        with st.expander(f"Comentário de {row['timestamp']}"):
                            st.markdown(f'<div class="comment-box">{row["comentario"]}</div>', unsafe_allow_html=True)
            else:
                st.info("Coluna de comentários não disponível no banco de dados.")
            
        else:
            st.info("Ainda não existem respostas HPO para analisar.")
    
    with tab3:
        st.subheader("Estatísticas das Respostas - Questionário de Liderança")
        
        df = load_lideranca_responses()
        
        if not df.empty:
            question_stats, overall_accuracy = calculate_lideranca_stats(df)
            
            st.subheader("Desempenho Geral")
            display_lideranca_stats(question_stats, overall_accuracy)
            
            # Comentários
            if 'comentario' in df.columns:
                comentarios_df = df[df['comentario'].notna() & (df['comentario'] != '')]
                if not comentarios_df.empty:
                    st.subheader("Comentários dos Participantes")
                    for idx, row in comentarios_df.iterrows():
                        with st.expander(f"Comentário de {row['timestamp']}"):
                            st.markdown(f'<div class="comment-box">{row["comentario"]}</div>', unsafe_allow_html=True)
            
        else:
            st.info("Ainda não existem respostas de Liderança para analisar.")
    
    with tab4:
        st.subheader("Relatórios de Análise")
        
        report_type = st.radio("Selecione o tipo de relatório:", 
                              ["HPO", "Liderança"],
                              horizontal=True)
        
        if report_type == "HPO":
            df = load_hpo_responses()
            
            if not df.empty:
                stats, performance, overall_performance, _ = calculate_hpo_stats(df)
                
                st.info("Gere relatórios detalhados com a análise completa dos dados do inquérito HPO.")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Relatório em HTML")
                    st.write("Relatório completo em formato HTML para visualização no navegador.")
                    
                    html_report = generate_hpo_html_report(stats, performance, overall_performance, df)
                    
                    st.download_button(
                        label="Descarregar Relatório HPO",
                        data=html_report,
                        file_name="relatorio_hpo.html",
                        mime="text/html",
                        use_container_width=True
                    )
                
                with col2:
                    st.subheader("Relatório para Impressão")
                    st.write("Gere um relatório otimizado para impressão ou conversão para PDF.")
                    
                    # Instruções para imprimir como PDF
                    st.info("""
                    **Para converter para PDF:**
                    1. Descarregue o relatório HTML
                    2. Abra-o no seu navegador
                    3. Use a opção 'Imprimir' do navegador
                    4. Escolha 'Guardar como PDF'
                    """)
                
                # Visualização prévia do relatório
                st.subheader("Pré-visualização do Relatório")
                with st.expander("Clique para ver a pré-visualização do relatório"):
                    # Mostrar uma versão simplificada do relatório
                    st.markdown(f"### Relatório HPO - Análise de Desempenho")
                    st.markdown(f"**Gerado em:** {datetime.now().strftime('%d/%m/%Y %H:%M')}")
                    st.markdown(f"**Total de respostas:** {len(df)}")
                    
                    if 'comentario' in df.columns:
                        comentarios_df = df[df['comentario'].notna() & (df['comentario'] != '')]
                        st.markdown(f"**Total de comentários:** {len(comentarios_df)}")
                    
                    st.markdown("#### Desempenho Geral")
                    st.markdown(f"**{overall_performance}**")
                    
                    st.markdown("#### Resultados por Dimensão")
                    for dim, avg_total in stats.items():
                        perf_class = ""
                        if performance[dim] == "Elevado desempenho":
                            perf_class = "good-performance"
                        elif performance[dim] == "Médio":
                            perf_class = "medium-performance"
                        else:
                            perf_class = "poor-performance"
                        
                        st.markdown(f"- **{dim}**: {avg_total:.2f}/14 - <span class='{perf_class}'>{performance[dim]}</span>", unsafe_allow_html=True)
            
            else:
                st.info("Ainda não existem respostas HPO para gerar relatórios.")
        
        else:  # Liderança
            df = load_lideranca_responses()
            
            if not df.empty:
                question_stats, overall_accuracy = calculate_lideranca_stats(df)
                
                st.info("Gere relatórios detalhados com a análise completa dos dados do inquérito de Liderança.")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Relatório em HTML")
                    st.write("Relatório completo em formato HTML para visualização no navegador.")
                    
                    html_report = generate_lideranca_html_report(question_stats, overall_accuracy, df)
                    
                    st.download_button(
                        label="Descarregar Relatório de Liderança",
                        data=html_report,
                        file_name="relatorio_lideranca.html",
                        mime="text/html",
                        use_container_width=True
                    )
                
                with col2:
                    st.subheader("Relatório para Impressão")
                    st.write("Gere um relatório otimizado para impressão ou conversão para PDF.")
                    
                    # Instruções para imprimir como PDF
                    st.info("""
                    **Para converter para PDF:**
                    1. Descarregue o relatório HTML
                    2. Abra-o no seu navegador
                    3. Use a opção 'Imprimir' do navegador
                    4. Escolha 'Guardar como PDF'
                    """)
                
                # Visualização prévia do relatório
                st.subheader("Pré-visualização do Relatório")
                with st.expander("Clique para ver a pré-visualização do relatório"):
                    # Mostrar uma versão simplificada do relatório
                    st.markdown(f"### Relatório de Liderança - Análise de Desempenho")
                    st.markdown(f"**Gerado em:** {datetime.now().strftime('%d/%m/%Y %H:%M')}")
                    st.markdown(f"**Total de respostas:** {len(df)}")
                    
                    if 'comentario' in df.columns:
                        comentarios_df = df[df['comentario'].notna() & (df['comentario'] != '')]
                        st.markdown(f"**Total de comentários:** {len(comentarios_df)}")
                    
                    st.markdown("#### Desempenho Geral")
                    st.markdown(f"**{overall_accuracy:.1f}% de acerto**")
                    
                    st.markdown("#### Resultados por Questão")
                    for q, stats in question_stats.items():
                        st.markdown(f"- **Questão {q}**: {stats['corretas']}/{stats['total']} ({stats['acuracia']:.1f}%)")
            
            else:
                st.info("Ainda não existem respostas de Liderança para gerar relatórios.")
    
    with tab5:
        st.subheader("Manutenção do Sistema")
        
        st.warning("⚠️ **Zona de Operações Críticas**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.info("**Reset Completo do Sistema**")
            st.write("Esta operação irá apagar permanentemente TODAS as respostas dos questionários e reiniciar o sistema.")
            st.error("**ATENÇÃO:** Esta ação não pode ser desfeita!")
            
            # Usar uma variável de sessão para controlar o estado de confirmação
            if 'reset_confirmed' not in st.session_state:
                st.session_state.reset_confirmed = False
            
            if not st.session_state.reset_confirmed:
                # Primeira etapa - pedir confirmação
                if st.button("🔄 Iniciar Reset do Sistema", key="start_reset", use_container_width=True):
                    st.session_state.reset_confirmed = True
                    st.rerun()
            else:
                # Segunda etapa - confirmações finais
                st.warning("Tem a certeza absoluta que deseja apagar TODOS os dados?")
                confirm1 = st.checkbox("Confirmo que compreendo que todos os dados serão PERDIDOS")
                confirm2 = st.checkbox("Confirmo que desejo prosseguir com o reset completo")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Confirmar Reset", key="confirm_reset", use_container_width=True, disabled=not (confirm1 and confirm2)):
                        if reset_entire_system():
                            st.success("Sistema resetado com sucesso! Todos os dados foram apagados.")
                            st.session_state.reset_confirmed = False
                            st.rerun()
                        else:
                            st.error("Erro ao resetar o sistema.")
                
                with col2:
                    if st.button("❌ Cancelar", key="cancel_reset", use_container_width=True):
                        st.session_state.reset_confirmed = False
                        st.rerun()
        
        with col2:
            st.info("**Estatísticas do Banco de Dados**")
            hpo_df = load_hpo_responses()
            lideranca_df = load_lideranca_responses()
            
            st.write(f"Total de respostas HPO: {len(hpo_df)}")
            st.write(f"Total de respostas Liderança: {len(lideranca_df)}")
            
            if not hpo_df.empty:
                st.write(f"Primeira resposta HPO: {hpo_df['timestamp'].min()}")
                st.write(f"Última resposta HPO: {hpo_df['timestamp'].max()}")
            
            if not lideranca_df.empty:
                st.write(f"Primeira resposta Liderança: {lideranca_df['timestamp'].min()}")
                st.write(f"Última resposta Liderança: {lideranca_df['timestamp'].max()}")

# Página principal
def main():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.role = None
        st.session_state.form_type = None
        st.session_state.submitted = False
    
    if not st.session_state.logged_in:
        login_page()
    else:
        # Botão de logout
        if st.sidebar.button("Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.role = None
            st.session_state.form_type = None
            st.session_state.submitted = False
            st.rerun()
        
        st.sidebar.write(f"Utilizador: {st.session_state.role}")
        
        if st.session_state.role == "trabalhador":
            if st.session_state.form_type is None:
                form_selection_page()
            elif st.session_state.form_type == "hpo":
                survey_hpo_page()
            elif st.session_state.form_type == "lideranca":
                survey_lideranca_page()
        elif st.session_state.role == "administrador":
            admin_page()
        elif st.session_state.role == "gestor":
            manager_page()

if __name__ == "__main__":
    # Inicializar banco de dados
    init_db()
    main()