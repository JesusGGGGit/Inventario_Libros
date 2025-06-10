import sqlite3
import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
import os
import sys
from datetime import datetime

# Detectar si se ejecuta como .exe o .py
base_dir = os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__))
db_path = os.path.join(base_dir, "libros.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Crear tabla si no existe
cursor.execute('''
CREATE TABLE IF NOT EXISTS libros (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fondo TEXT,
    codigo_barras TEXT UNIQUE,
    clasificacion TEXT,
    bibid TEXT,
    tipo TEXT,
    estado TEXT,
    copias TEXT,
    volumen TEXT,
    edicion TEXT,
    titulo TEXT,
    autor TEXT,
    editorial TEXT,
    anio TEXT,
    escaneado INTEGER DEFAULT 0,
    manual INTEGER DEFAULT 0
)
''')
conn.commit()

# Crear tabla de historial si no existe
cursor.execute('''
CREATE TABLE IF NOT EXISTS historial (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo_barras TEXT,
    accion TEXT,
    detalles TEXT,
    fecha TEXT
)
''')
conn.commit()



# Opciones de estado
ESTADOS = [
    "Disponible", "Sólo préstamo en sala", "Averiado",
    "En catalogación", "Estantería en reparación", "Prestado", "Retenido", "Perdido", "Cancelado", "Reparación"
]
mostrar_escaneados = True

def toggle_escaneados():
    global mostrar_escaneados
    mostrar_escaneados = not mostrar_escaneados
    actualizar_tabla_perdidos()

# Registrar acción en el historial
def registrar_historial(codigo_barras, accion, detalles):
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO historial (codigo_barras, accion, detalles, fecha) VALUES (?, ?, ?, ?)",
        (codigo_barras, accion, detalles, fecha_actual)
    )
    conn.commit()
   # Registrar acción en el historial
# Registrar acción en el historial
def registrar_historial(codigo_barras, accion, detalles):
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO historial (codigo_barras, accion, detalles, fecha) VALUES (?, ?, ?, ?)",
        (codigo_barras, accion, detalles, fecha_actual)
    )
    conn.commit()

def buscar_libro(event=None):
    if event is not None and not isinstance(event, str):
        ventana.focus_force()

    codigo = entry_codigo.get().strip()

    if not codigo:
        messagebox.showwarning("Advertencia", "Introduce un código de barras.")
        return

    cursor.execute("SELECT * FROM libros WHERE codigo_barras = ?", (codigo,))
    libro = cursor.fetchone()

    if libro:
        if libro[14] == 1:
            messagebox.showinfo("Información", f"🔁 Ya escaneado: {libro[10]} ({codigo})")
        else:
            if libro[6] == "Perdido":
                respuesta = messagebox.askyesno(
                    "Libro perdido",
                    f"Este libro está marcado como PERDIDO: {libro[10]} ({codigo}).\n¿Quieres cambiar su estado?"
                )
                if respuesta:
                    nuevo_estado = simpledialog.askstring(
                        "Cambiar Estado",
                        f"Introduce nuevo estado para el libro (Opciones: {', '.join(ESTADOS)}):",
                        parent=ventana
                    )
                    if nuevo_estado and nuevo_estado in ESTADOS:
                        cursor.execute(
                            "UPDATE libros SET estado = ?, escaneado = 1 WHERE codigo_barras = ?",
                            (nuevo_estado, codigo)
                        )
                        registrar_historial(codigo, "Cambio de Estado", f"Se cambió el estado a {nuevo_estado}")
                    else:
                        cursor.execute("UPDATE libros SET escaneado = 1 WHERE codigo_barras = ?", (codigo,))
                        registrar_historial(codigo, "Escaneo", "Se escaneó el libro")
                else:
                    cursor.execute("UPDATE libros SET escaneado = 1 WHERE codigo_barras = ?", (codigo,))
                    registrar_historial(codigo, "Escaneo", "Se escaneó el libro")
                conn.commit()
            else:
                cursor.execute("UPDATE libros SET escaneado = 1 WHERE codigo_barras = ?", (codigo,))
                registrar_historial(codigo, "Escaneo", "Se escaneó el libro")
                conn.commit()
    else:
        if messagebox.askyesno("Libro no encontrado", f"❌ Código {codigo} no está en la base.\n¿Quieres agregarlo manualmente?"):
            nuevo_libro = {}
            campos = [
                ("Fondo", ""), ("Clasificación", ""), ("BibId", ""), ("Tipo", ""), ("Estado", "Disponible"),
                ("Copias", ""), ("Volumen", ""), ("Edición", ""), ("Título", ""), ("Autor", ""),
                ("Editorial", ""), ("Año", "")
            ]
            for campo, valor_defecto in campos:
                valor = simpledialog.askstring("Agregar Libro", f"{campo}:", initialvalue=valor_defecto)
                if valor is None:
                    messagebox.showwarning("Cancelado", "Libro no agregado.")
                    return
                nuevo_libro[campo.lower()] = valor

            try:
                cursor.execute('''
                    INSERT INTO libros (
                        fondo, codigo_barras, clasificacion, bibid, tipo, estado,
                        copias, volumen, edicion, titulo, autor, editorial, anio,
                        escaneado, manual
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1)
                ''', (
                    nuevo_libro['fondo'], codigo, nuevo_libro['clasificación'], nuevo_libro['bibid'],
                    nuevo_libro['tipo'], nuevo_libro['estado'], nuevo_libro['copias'],
                    nuevo_libro['volumen'], nuevo_libro['edición'], nuevo_libro['título'],
                    nuevo_libro['autor'], nuevo_libro['editorial'], nuevo_libro['año']
                ))
                conn.commit()
                registrar_historial(codigo, "Agregado Manual", f"Se agregó manualmente el libro: {nuevo_libro['título']}")
                messagebox.showinfo("Agregado", f"✅ Libro agregado manualmente: {nuevo_libro['título']}")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo agregar el libro:\n{e}")

    entry_codigo.delete(0, tk.END)
    entry_codigo.focus_set()
    actualizar_tabla_perdidos()
    actualizar_tabla_escaneados()
    actualizar_tabla_historial()


def importar_varios_archivos():
    archivos = filedialog.askopenfilenames(filetypes=[("SQLite Database", "*.db")])
    if not archivos:
        return

    for archivo in archivos:
        try:
            # Conectar a la base de datos externa
            conn_externa = sqlite3.connect(archivo)
            cursor_externa = conn_externa.cursor()

            # Obtener registros de la tabla libros de la base de datos externa
            cursor_externa.execute("SELECT * FROM libros")
            libros_externos = cursor_externa.fetchall()

            for libro_externo in libros_externos:
                codigo_barras = libro_externo[2]  # Ajusta este índice si es necesario

                # Verificar si el libro ya existe en la base de datos actual
                cursor.execute("SELECT * FROM libros WHERE codigo_barras = ?", (codigo_barras,))
                libro_actual = cursor.fetchone()

                if libro_actual:
                    # Obtener nombres de columnas
                    columnas = [desc[0] for desc in cursor.description]

                    # Comparar campo por campo (excepto ID y 'escaneado')
                    diferencias = []
                    for i in range(1, len(libro_actual)):
                        if columnas[i] == "escaneado":
                            continue  # Saltar comparación del campo escaneado
                        if libro_actual[i] != libro_externo[i]:
                            diferencias.append(
                                f"{columnas[i]}:\n  Actual: {libro_actual[i]}\n  Nuevo:  {libro_externo[i]}"
                            )

                    # Si hay diferencias (excluyendo escaneado), preguntar al usuario
                    if diferencias:
                        mensaje = f"⚠️ El libro con código de barras {codigo_barras} tiene diferencias:\n\n"
                        mensaje += "\n\n".join(diferencias)
                        mensaje += "\n\n¿Deseas reemplazar los datos actuales con los nuevos?"

                        if messagebox.askyesno("Conflicto de datos", mensaje):
                            cursor.execute('''
                                UPDATE libros SET
                                    fondo = ?, codigo_barras = ?, clasificacion = ?, bibid = ?, tipo = ?, estado = ?,
                                    copias = ?, volumen = ?, edicion = ?, titulo = ?, autor = ?, editorial = ?,
                                    anio = ?, escaneado = ?, manual = ?
                                WHERE codigo_barras = ?
                            ''', (*libro_externo[1:16], codigo_barras))
                    else:
                        # Actualizar campo escaneado solo si pasa de 0 a 1 (nunca bajar de 1 a 0)
                        escaneado_actual = libro_actual[columnas.index("escaneado")]
                        escaneado_externo = libro_externo[columnas.index("escaneado")]

                        if escaneado_externo == 1 and escaneado_actual != 1:
                            cursor.execute('''
                                UPDATE libros SET escaneado = ? WHERE codigo_barras = ?
                            ''', (escaneado_externo, codigo_barras))
                else:
                    # Si no existe, insertar nuevo libro
                    cursor.execute('''
                        INSERT INTO libros (
                            fondo, codigo_barras, clasificacion, bibid, tipo, estado,
                            copias, volumen, edicion, titulo, autor, editorial, anio, escaneado, manual
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', libro_externo[:15])

            # Procesar historial
            cursor_externa.execute("SELECT * FROM historial")
            historial_externo = cursor_externa.fetchall()

            for registro in historial_externo:
                cursor.execute('''
                    INSERT OR IGNORE INTO historial (
                        codigo_barras, accion, detalles, fecha
                    ) VALUES (?, ?, ?, ?)
                ''', registro[1:])

            conn.commit()
            conn_externa.close()

        except Exception as e:
            messagebox.showerror("Error al importar", str(e))

    messagebox.showinfo("Importación exitosa", "✅ Archivos importados correctamente.")
    actualizar_tabla_perdidos()
    actualizar_tabla_escaneados()
    actualizar_tabla_historial()

def importar_archivo():
    archivo = filedialog.askopenfilename(filetypes=[("CSV/Excel", "*.csv *.xlsx")])
    if not archivo:
        return

    try:
        # Leer el archivo
        df = pd.read_csv(archivo) if archivo.endswith('.csv') else pd.read_excel(archivo)

        # Crear ventana emergente para vista previa
        ventana_previa = tk.Toplevel(ventana)
        ventana_previa.title("Vista Previa de Datos")

        # Crear Treeview para vista previa
        tree_previa = ttk.Treeview(ventana_previa)
        tree_previa.pack(fill='both', expand=True)

        tree_previa["columns"] = list(df.columns)
        for idx, col in enumerate(df.columns, start=1):
            tree_previa.heading(col, text=f"{idx}: {col}")
            tree_previa.column(col, width=100, anchor=tk.W)

        for i, row in df.head(10).iterrows():
            tree_previa.insert("", "end", values=list(row))

        # Frame para edición de nombres
        frame_edicion = tk.Frame(ventana_previa)
        frame_edicion.pack(fill='x', padx=10, pady=10)

        columnas_esperadas = [
            'Fondo', 'Código Barras', 'Clasificación', 'BibId', 'Tipo',
            'Estado', 'Copias', 'Volumen', 'Edición', 'Título', 'Autor', 'Editorial', 'Año'
        ]

        entradas_columnas = {}
        etiquetas_estado = {}

        def actualizar_estado(event=None):
            for col_original, entrada in entradas_columnas.items():
                valor = entrada.get()
                etiqueta = etiquetas_estado[col_original]
                if valor in columnas_esperadas:
                    etiqueta.config(text="✓ Esperada", foreground="green")
                else:
                    etiqueta.config(text="✗ No esperada/Adicional", foreground="red")

        # Crear entradas y etiquetas de estado
        for i, col in enumerate(df.columns):
            tk.Label(frame_edicion, text=f"Columna {i + 1}:").grid(row=i, column=0, padx=5, pady=5)
            entrada = ttk.Combobox(frame_edicion, values=columnas_esperadas, width=30)
            entrada.insert(0, col)
            entrada.grid(row=i, column=1, padx=5, pady=5)
            entrada.bind("<<ComboboxSelected>>", actualizar_estado)
            entrada.bind("<KeyRelease>", actualizar_estado)
            entradas_columnas[col] = entrada

            etiqueta = tk.Label(frame_edicion, text="")
            etiqueta.grid(row=i, column=2, padx=5, pady=5)
            etiquetas_estado[col] = etiqueta

        actualizar_estado()

        def confirmar_importacion():
            nuevos_nombres = {viejo: entrada.get() for viejo, entrada in entradas_columnas.items()}
            df.rename(columns=nuevos_nombres, inplace=True)

            columnas_faltantes = [col for col in columnas_esperadas if col not in df.columns]
            if columnas_faltantes:
                mensaje = f"Faltan las siguientes columnas: {', '.join(columnas_faltantes)}. ¿Deseas agregarlas aunque estén vacías?"
                if messagebox.askyesno("Columnas Faltantes", mensaje):
                    for col in columnas_faltantes:
                        df[col] = ''

            columnas_adicionales = [col for col in df.columns if col not in columnas_esperadas]
            if columnas_adicionales:
                mensaje = f"Hay columnas adicionales: {', '.join(columnas_adicionales)}. ¿Deseas agregarlas a la base de datos?"
                if messagebox.askyesno("Columnas Adicionales", mensaje):
                    for col in columnas_adicionales:
                        try:
                            cursor.execute(f'ALTER TABLE libros ADD COLUMN "{col}" TEXT')
                            conn.commit()
                        except Exception as e:
                            print(f"Error agregando columna {col}: {e}")

            for _, fila in df.iterrows():
                try:
                    # Insert solo con columnas esperadas (igual que antes)
                    fila_completa = {col: fila.get(col, '') for col in columnas_esperadas}
                    cursor.execute('''
                        INSERT OR IGNORE INTO libros (
                            fondo, codigo_barras, clasificacion, bibid, tipo, estado,
                            copias, volumen, edicion, titulo, autor, editorial, anio, escaneado, manual
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0)
                    ''', (
                        fila_completa['Fondo'], fila_completa['Código Barras'], fila_completa['Clasificación'],
                        fila_completa['BibId'], fila_completa['Tipo'], fila_completa['Estado'],
                        fila_completa['Copias'], fila_completa['Volumen'], fila_completa['Edición'],
                        fila_completa['Título'], fila_completa['Autor'], fila_completa['Editorial'],
                        str(fila_completa['Año'])
                    ))

                    # Ahora actualizamos las columnas adicionales en esa fila, usando código_barras como identificador
                    if columnas_adicionales:
                        set_clauses = ', '.join([f'"{col}" = ?' for col in columnas_adicionales])
                        valores_adicionales = [fila.get(col, '') for col in columnas_adicionales]
                        valores_adicionales.append(fila_completa['Código Barras'])  # para el WHERE
                        query_update = f'UPDATE libros SET {set_clauses} WHERE codigo_barras = ?'
                        cursor.execute(query_update, valores_adicionales)

                except Exception as e:
                    print(f"Error en fila: {fila}\n{e}")

            conn.commit()
            messagebox.showinfo("Importación exitosa", "✅ Libros importados correctamente.")
            actualizar_tabla_perdidos()
            actualizar_tabla_escaneados()
            ventana_previa.destroy()


        tk.Button(ventana_previa, text="Confirmar Importación", command=confirmar_importacion).pack(pady=10)

    except Exception as e:
        messagebox.showerror("Error al importar", str(e))





def exportar_a_excel():
    carpeta = filedialog.askdirectory(title="Selecciona una carpeta para guardar")
    if not carpeta:
        return
    try:
        # Paso 1: Obtener columnas reales de la tabla, excluyendo algunas
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(libros)")
        todas_columnas = [fila[1] for fila in cursor.fetchall()]
        columnas_excluir = {'id', 'escaneado', 'manual'}
        columnas_usar = [col for col in todas_columnas if col not in columnas_excluir]

            # Escapar nombres de columnas por si tienen caracteres raros
        columnas_str = ", ".join([f'"{col}"' for col in columnas_usar])
        query_base = f"SELECT {columnas_str} FROM libros"

        # Paso 3: Leer los datos
        df_todos = pd.read_sql_query(query_base, conn)
        df_escaneados = pd.read_sql_query(query_base + " WHERE escaneado = 1", conn)
        df_perdidos = pd.read_sql_query(query_base + " WHERE escaneado = 0", conn)
        df_manuales = pd.read_sql_query(query_base + " WHERE manual = 1", conn)
        df_estados_raros = pd.read_sql_query(
            query_base + " WHERE estado NOT IN (" + ",".join(["?"] * len(ESTADOS)) + ")",
            conn, params=ESTADOS
        )

        # Paso 4: Renombrar columnas opcionalmente (si quieres nombres amigables)
        nombres_columnas = {
            'fondo': 'Fondo',
            'codigo_barras': 'Código Barras',
            'clasificacion': 'Clasificación',
            'bibid': 'BibId',
            'tipo': 'Tipo',
            'estado': 'Estado',
            'copias': 'Cop.',
            'volumen': 'Volumen',
            'edicion': 'Edic.',
            'titulo': 'Título',
            'autor': 'Autor',
            'editorial': 'Editorial',
            'anio': 'Año'
        }

        for df in [df_todos, df_escaneados, df_perdidos, df_manuales, df_estados_raros]:
            df.rename(columns={col: nombres_columnas.get(col, col) for col in df.columns}, inplace=True)

        # Paso 5: Exportar a Excel
        df_todos.to_excel(os.path.join(carpeta, "libros_completos.xlsx"), index=False)
        df_escaneados.to_excel(os.path.join(carpeta, "libros_escaneados.xlsx"), index=False)
        df_perdidos.to_excel(os.path.join(carpeta, "libros_perdidos_o_no_escaneados.xlsx"), index=False)
        df_manuales.to_excel(os.path.join(carpeta, "libros_agregados_manual.xlsx"), index=False)
        df_estados_raros.to_excel(os.path.join(carpeta, "libros_estados_raros.xlsx"), index=False)

        # Paso 6: Respaldo de la base de datos
        respaldo_db = os.path.join(carpeta, "respaldo_libros.db")
        conn_backup = sqlite3.connect(respaldo_db)
        conn.backup(conn_backup)
        conn_backup.close()

        messagebox.showinfo("Exportación exitosa", "✅ Archivos exportados correctamente.")
    except Exception as e:
        messagebox.showerror("Error al exportar", str(e))


def editar_campo_libro(event):
    item = tree_perdidos.selection()[0]
    valores = tree_perdidos.item(item, 'values')
    codigo_barras = valores[1]  # Código de barras siempre está en la posición 1
    
    col = tree_perdidos.identify_column(event.x)
    col_index = int(str(col).replace('#', '')) - 1
    if col_index < 0:
        return
    
    campo = cols[col_index]
    valor_actual = valores[col_index]
    
    nuevo_valor = simpledialog.askstring("Editar Campo", f"{campo}:", initialvalue=valor_actual)
    if nuevo_valor is not None:
        try:
            # Mapear nombres de columnas del Treeview a nombres de columnas de la base de datos
            mapa_columnas = {
                "Fondo": "fondo",
                "Código Barras": "codigo_barras",
                "Clasificación": "clasificacion",
                "BibId": "bibid",
                "Tipo": "tipo",
                "Estado": "estado",
                "Copias": "copias",
                "Volumen": "volumen",
                "Edición": "edicion",
                "Título": "titulo",
                "Autor": "autor",
                "Editorial": "editorial",
                "Año": "anio"
            }
            
            nombre_columna_db = mapa_columnas.get(campo)
            if not nombre_columna_db:
                raise ValueError(f"Columna {campo} no mapeada")
            
            cursor.execute(f"UPDATE libros SET {nombre_columna_db} = ? WHERE codigo_barras = ?", 
                          (nuevo_valor, codigo_barras))
            conn.commit()
            
            # Para cambios en clasificación, actualizar también el historial
            if campo == "Clasificación":
                cursor.execute("SELECT titulo FROM libros WHERE codigo_barras = ?", (codigo_barras,))
                titulo = cursor.fetchone()[0]
                registrar_historial(codigo_barras, "Edición Clasificación", 
                                  f"De '{valor_actual}' a '{nuevo_valor}' - Título: {titulo}")
            else:
                registrar_historial(codigo_barras, "Edición", f"Campo '{campo}' editado")
                
            messagebox.showinfo("Editado", f"✅ Campo '{campo}' editado correctamente.")
            actualizar_tabla_perdidos()
            actualizar_tabla_escaneados()
            actualizar_tabla_historial()
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo editar el campo:\n{e}")

def actualizar_tabla_perdidos():
    for item in tree_perdidos.get_children():
        tree_perdidos.delete(item)

    where_clauses = []
    params = []

    estados_seleccionados = [estado for estado, var in filtros_estado.items() if var.get() == 1]
    if estados_seleccionados:
        placeholders = ",".join("?" for _ in estados_seleccionados)
        where_clauses.append(f"estado IN ({placeholders})")
        params.extend(estados_seleccionados)

    if var_escaneado.get() == 1 and var_no_escaneado.get() == 0:
        where_clauses.append("escaneado = 1")
    elif var_no_escaneado.get() == 1 and var_escaneado.get() == 0:
        where_clauses.append("escaneado = 0")

    if var_estados_raros.get() == 1:
        placeholders = ",".join("?" for _ in ESTADOS)
        where_clauses.append(f"estado NOT IN ({placeholders})")
        params.extend(ESTADOS)

    where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    query = f"SELECT fondo, codigo_barras, clasificacion, bibid, tipo, estado, copias, volumen, edicion, titulo, autor, editorial, anio, escaneado FROM libros{where_sql} ORDER BY codigo_barras"
    cursor.execute(query, params)
    libros = cursor.fetchall()

    for libro in libros:
        tags = ('escaneado',) if libro[13] == 1 else ()
        if not mostrar_escaneados and 'escaneado' in tags:
            continue
        tree_perdidos.insert("", tk.END, values=libro[:-1], tags=tags)

    total = len(libros)
    escaneados = sum(1 for libro in libros if libro[-1] == 1)
    porcentaje = (escaneados / total * 100) if total > 0 else 0
    label_contador.config(text=f"Escaneados: {escaneados} / {total} ({porcentaje:.1f}%)")

def actualizar_tabla_escaneados():
    for item in tree_escaneados.get_children():
        tree_escaneados.delete(item)

    cursor.execute("SELECT fondo, codigo_barras, clasificacion, bibid, tipo, estado, copias, volumen, edicion, titulo, autor, editorial, anio FROM libros WHERE escaneado = 1 ORDER BY codigo_barras")
    libros = cursor.fetchall()

    for libro in libros:
        tree_escaneados.insert("", tk.END, values=libro)

def actualizar_tabla_historial():
    for item in tree_historial.get_children():
        tree_historial.delete(item)

    cursor.execute("""
        SELECT h.codigo_barras, l.clasificacion, l.titulo, h.accion, h.detalles, h.fecha
        FROM historial h
        LEFT JOIN libros l ON h.codigo_barras = l.codigo_barras
        ORDER BY h.fecha DESC
    """)
    registros = cursor.fetchall()

    for registro in registros:
        tree_historial.insert("", tk.END, values=registro)
import unicodedata

def eliminar_acentos(cadena):
    if not isinstance(cadena, str):
        return cadena
    # Normaliza la cadena a su forma normal 'NFKD' y luego elimina los caracteres que no son ASCII
    return ''.join(
        c for c in unicodedata.normalize('NFKD', cadena)
        if not unicodedata.combining(c)
    )

# Asegúrate de que la función esté registrada en la conexión de SQLite
conn.create_function("ELIMINAR_ACENTOS", 1, eliminar_acentos)
def buscar_libro_especifico():
    criterio = simpledialog.askstring("Buscar Libro", "Ingrese el título, autor o código de barras del libro:")

    if not criterio:
        return

    try:
        criterio_sin_acentos = eliminar_acentos(criterio).lower()

        # Obtener columnas de la tabla y excluir id, escaneado, manual
        cursor.execute("PRAGMA table_info(libros)")
        columnas_info = cursor.fetchall()
        excluir = {'id', 'escaneado', 'manual'}
        columnas = [col[1] for col in columnas_info if col[1] not in excluir]

        # Construir consulta con columnas filtradas
        campos_str = ", ".join(columnas)

        consulta = f'''
            SELECT {campos_str} FROM libros
            WHERE LOWER(ELIMINAR_ACENTOS(titulo)) LIKE ? OR
                  LOWER(ELIMINAR_ACENTOS(autor)) LIKE ? OR
                  LOWER(ELIMINAR_ACENTOS(codigo_barras)) LIKE ?
        '''

        cursor.execute(consulta, (f'%{criterio_sin_acentos}%',)*3)
        libros = cursor.fetchall()

        if libros:
            ventana_resultados = tk.Toplevel(ventana)
            ventana_resultados.title("Resultados de la Búsqueda")

            tree_resultados = ttk.Treeview(ventana_resultados, columns=columnas, show='headings')
            for c in columnas:
                tree_resultados.heading(c, text=c)
                tree_resultados.column(c, width=100, anchor=tk.W)

            for libro in libros:
                tree_resultados.insert("", tk.END, values=libro)

            tree_resultados.pack(fill='both', expand=True)
            tk.Button(ventana_resultados, text="Cerrar", command=ventana_resultados.destroy).pack(pady=10)
        else:
            messagebox.showinfo("Resultados", "No se encontraron libros que coincidan con el criterio de búsqueda.")

    except Exception as e:
        messagebox.showerror("Error", f"No se pudo realizar la búsqueda:\n{e}")




# GUI
ventana = tk.Tk()
ventana.title("Gestor de Libros")
ventana.geometry("1200x800")

# Frame principal para los controles superiores
frame_controles = tk.Frame(ventana)
frame_controles.pack(pady=10, fill=tk.X)

# Frame para el escaneo de códigos
frame_escaneo = tk.LabelFrame(frame_controles, text="Escaneo", padx=5, pady=5)
frame_escaneo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

tk.Label(frame_escaneo, text="Código de Barras:").pack(side=tk.LEFT, padx=5)
entry_codigo = tk.Entry(frame_escaneo, width=30)
entry_codigo.pack(side=tk.LEFT, padx=5)
entry_codigo.bind('<Return>', buscar_libro)
tk.Button(frame_escaneo, text="📦 Escanear", command=buscar_libro).pack(side=tk.LEFT, padx=5)
tk.Button(frame_escaneo, text="🔍 Buscar Libro", command=buscar_libro_especifico).pack(side=tk.LEFT, padx=5)


# Frame para botones de importación/exportación
frame_import_export = tk.LabelFrame(frame_controles, text="Importar/Exportar", padx=5, pady=5)
frame_import_export.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

tk.Button(frame_import_export, text="📁 CSV/Excel", command=importar_archivo).pack(side=tk.LEFT, padx=2)
tk.Button(frame_import_export, text="📥 Múltiples DB", command=importar_varios_archivos).pack(side=tk.LEFT, padx=2)
tk.Button(frame_import_export, text="📤 Exportar", command=exportar_a_excel).pack(side=tk.LEFT, padx=2)

# Frame para controles de visualización
frame_visualizacion = tk.LabelFrame(frame_controles, text="Visualización", padx=5, pady=5)
frame_visualizacion.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

tk.Button(frame_visualizacion, text="👁 Mostrar/Ocultar Escaneados", command=toggle_escaneados).pack(side=tk.LEFT, padx=5)

# Contador
label_contador = tk.Label(ventana, text="Escaneados: 0 / 0 (0.0%)", font=("Arial", 12, "bold"))
label_contador.pack(pady=5)

# Filtros
frame_filtros = tk.LabelFrame(ventana, text="Filtros por Estado", padx=5, pady=5)
frame_filtros.pack(fill=tk.X, padx=10, pady=5)

filtros_estado = {}
for i, estado in enumerate(ESTADOS):
    var = tk.IntVar(value=0)  # Por defecto todos activados
    chk = tk.Checkbutton(frame_filtros, text=estado, variable=var, command=actualizar_tabla_perdidos)
    chk.grid(row=i // 4, column=i % 4, sticky="w", padx=5, pady=2)
    filtros_estado[estado] = var

# Filtros adicionales
frame_filtros_extra = tk.Frame(frame_filtros)
frame_filtros_extra.grid(row=len(ESTADOS)//4 + 1, column=0, columnspan=4, pady=5)

var_escaneado = tk.IntVar()
chk_escaneado = tk.Checkbutton(frame_filtros_extra, text="Solo escaneados", variable=var_escaneado, command=actualizar_tabla_perdidos)
chk_escaneado.pack(side=tk.LEFT, padx=10)

var_no_escaneado = tk.IntVar()
chk_no_escaneado = tk.Checkbutton(frame_filtros_extra, text="Solo no escaneados", variable=var_no_escaneado, command=actualizar_tabla_perdidos)
chk_no_escaneado.pack(side=tk.LEFT, padx=10)

var_estados_raros = tk.IntVar()
chk_estados_raros = tk.Checkbutton(frame_filtros_extra, text="Estados no estándar", variable=var_estados_raros, command=actualizar_tabla_perdidos)
chk_estados_raros.pack(side=tk.LEFT, padx=10)

cols = ("Fondo", "Código Barras", "Clasificación", "BibId", "Tipo", "Estado",
        "Copias", "Volumen", "Edición", "Título", "Autor", "Editorial", "Año")

cols_historial = ("Código Barras", "Clasificación", "Título", "Acción", "Detalles", "Fecha")

def crear_tabla(titulo):
    frame = tk.LabelFrame(frame_tablas, text=titulo)
    frame.pack(fill='both', expand=True)
    contenedor = tk.Frame(frame)
    contenedor.pack(fill='both', expand=True)
    tree = ttk.Treeview(contenedor, columns=cols, show='headings')
    for c in cols:
        tree.heading(c, text=c)
        tree.column(c, width=100, anchor=tk.W)
    scroll_y = ttk.Scrollbar(contenedor, orient="vertical", command=tree.yview)
    scroll_x = ttk.Scrollbar(contenedor, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
    tree.grid(row=0, column=0, sticky='nsew')
    scroll_y.grid(row=0, column=1, sticky='ns')
    scroll_x.grid(row=1, column=0, sticky='ew')
    contenedor.grid_rowconfigure(0, weight=1)
    contenedor.grid_columnconfigure(0, weight=1)
    return tree

def crear_tabla_historial(titulo):
    frame = tk.LabelFrame(frame_tablas_historial, text=titulo)
    frame.pack(fill='both', expand=True)
    contenedor = tk.Frame(frame)
    contenedor.pack(fill='both', expand=True)
    tree = ttk.Treeview(contenedor, columns=cols_historial, show='headings')
    for c in cols_historial:
        tree.heading(c, text=c)
        tree.column(c, width=100, anchor=tk.W)
    scroll_y = ttk.Scrollbar(contenedor, orient="vertical", command=tree.yview)
    scroll_x = ttk.Scrollbar(contenedor, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
    tree.grid(row=0, column=0, sticky='nsew')
    scroll_y.grid(row=0, column=1, sticky='ns')
    scroll_x.grid(row=1, column=0, sticky='ew')
    contenedor.grid_rowconfigure(0, weight=1)
    contenedor.grid_columnconfigure(0, weight=1)
    return tree

# Crear pestañas
notebook = ttk.Notebook(ventana)
notebook.pack(fill='both', expand=True)

# Pestaña principal
frame_principal = ttk.Frame(notebook)
notebook.add(frame_principal, text="Principal")

frame_tablas = tk.Frame(frame_principal)
frame_tablas.pack(fill='both', expand=True, padx=10, pady=10)

tree_perdidos = crear_tabla("Libros en Base de Datos Filtrados")
tree_perdidos.tag_configure('escaneado', background='#d4f4dd')
tree_perdidos.bind("<Double-1>", editar_campo_libro)
tree_escaneados = crear_tabla("Libros Escaneados")

# Pestaña de historial
frame_historial = ttk.Frame(notebook)
notebook.add(frame_historial, text="Historial")
frame_tablas_historial = tk.Frame(frame_historial)
frame_tablas_historial.pack(fill='both', expand=True, padx=10, pady=10)
tree_historial = crear_tabla_historial("Historial de Movimientos")

# Iniciar
actualizar_tabla_perdidos()
actualizar_tabla_escaneados()
actualizar_tabla_historial()
ventana.mainloop()
conn.close() 