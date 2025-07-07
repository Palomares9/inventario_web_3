from tkinter import *
from tkinter import messagebox, ttk
from PIL import Image, ImageTk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from pymongo import MongoClient

class DBConnection:
    def __init__(self):
        self.client = MongoClient("mongodb+srv://Palomares:Palomares1234@cluster0.uuqmeq8.mongodb.net/")
        self.db = self.client["sistema_inventario_mongo"]
        self.usuarios = self.db["usuarioos"]
        self.inventario = self.db["inventario"]

    def verificar_usuario(self, usuario, contraseña):
        return self.usuarios.find_one({"Nombre": usuario, "Contra": contraseña})

    def registrar_usuario(self, usuario, contraseña, permiso):
        nuevo_usuario = {
            "Nombre": usuario,
            "Contra": contraseña,
            "Tipo_u": permiso,
            "Ap_p": "",
            "Ap_m": ""
        }
        try:
            self.usuarios.insert_one(nuevo_usuario)
            return True
        except Exception as e:
            print("Error al registrar:", e)
            return False

    def agregar_producto(self, datos):
        producto = {
            "ID_Prod": datos['código'],
            "Descrip": datos['nombre'],
            "Precio": datos['precio'],
            "Cant": datos['stock'],
            "Marca": datos.get('marca', ''),
            "medida": datos.get('medida', '')
        }
        try:
            self.inventario.insert_one(producto)
            return True
        except Exception as e:
            print("Error al agregar producto:", e)
            return False

    def modificar_producto(self, datos):
        query = {"ID_Prod": datos['código']}
        nuevos_datos = {
            "$set": {
                "Descrip": datos['nombre'],
                "Precio": datos['precio'],
                "Cant": datos['stock'],
                "Marca": datos.get('marca', ''),
                "medida": datos.get('medida', '')
            }
        }
        resultado = self.inventario.update_one(query, nuevos_datos)
        return resultado.modified_count > 0

    def eliminar_producto(self, codigo):
        resultado = self.inventario.delete_one({"ID_Prod": int(codigo)})
        return resultado.deleted_count > 0

    def obtener_productos(self):
        return list(self.inventario.find())

    def buscar_producto(self, entrada):
        if entrada.isdigit():
            filtro = {"ID_Prod": int(entrada)}
        else:
            filtro = {"Descrip": entrada}
        return self.inventario.find_one(filtro)

# ===== Clase principal del sistema de inventario =====
class InventarioApp:
    def __init__(self, root, db, permiso_usuario):
        self.db = db
        self.permiso_usuario = permiso_usuario
        self.root = root
        self.root.title("Inventario de Ferretería")
        self.root.geometry("1000x600")

        self.productos = {}
        self.historial_ventas = []

        # INTERFAZ
        self.main_frame = Frame(root)
        self.main_frame.pack(fill="both", expand=True)

        fondo_menu = "#fa860b"
        fondo_activo = "#1f2a38"
        fondo_contenido = "#FFFFFF"
        texto_claro = "#FFFFFF"

        self.menu_frame = Frame(self.main_frame, bg=fondo_menu, width=200)
        self.menu_frame.pack(side="left", fill="y")

        try:
            imagen = Image.open("logo.png")
            imagen = imagen.resize((150, 150), Image.ANTIALIAS)
            self.logo_img = ImageTk.PhotoImage(imagen)
            logo_label = Label(self.menu_frame, image=self.logo_img, bg=fondo_menu)
            logo_label.pack(pady=20)
        except:
            logo_label = Label(self.menu_frame, text="FERRETERÍA", bg=fondo_menu, fg=texto_claro,
                               font=("Arial", 16, "bold"))
            logo_label.pack(pady=20)

        self.content_frame = Frame(self.main_frame, bg=fondo_contenido)
        self.content_frame.pack(side="right", expand=True, fill="both")

        self.secciones = {
            "🏠 Dashboard": self.crear_tab_dashboard,
            "📦 Inventario": self.crear_tab_inventario,
            "➕ Agregar Producto": self.crear_tab_agregar,
            "🔍 Buscar Producto": self.crear_tab_buscar,
            "🛒 Realizar Venta": self.crear_tab_ventas,
            "📜 Historial de Ventas": self.crear_tab_historial,
        }
        for texto, funcion in self.secciones.items():
            btn = Button(self.menu_frame, text=texto, bg=fondo_menu, fg=texto_claro, relief="flat",
                         font=("Arial", 12), padx=10, pady=10, anchor="w",
                         activebackground=fondo_activo, activeforeground=texto_claro,
                         command=lambda f=funcion: self.mostrar_seccion(f))
            btn.pack(fill="x", padx=5, pady=5)

        self.cargar_productos()
        self.mostrar_seccion(self.crear_tab_dashboard)

    def cargar_productos(self):
        self.productos = {}
        for prod in self.db.obtener_productos():
            self.productos[prod['codigo']] = prod

    def mostrar_seccion(self, seccion_func):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        if seccion_func == self.crear_tab_agregar and self.permiso_usuario not in ('admin', 'editor'):
            Label(self.content_frame, text="No tiene permiso para agregar productos.", fg="red", font=("Arial", 16)).pack(pady=50)
        elif seccion_func == self.crear_tab_historial and self.permiso_usuario == 'consulta':
            Label(self.content_frame, text="No tiene permiso para ver ventas.", fg="red", font=("Arial", 16)).pack(pady=50)
        else:
            seccion_func()

    # -------------------- DASHBOARD --------------------
    def crear_tab_dashboard(self):
        frame = ttk.Frame(self.content_frame)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Resumen del Inventario", font=("Arial", 18)).pack(pady=15)

        self.total_productos_var = StringVar()
        self.bajo_stock_var = StringVar()
        self.categorias_var = StringVar()

        datos_frame = ttk.Frame(frame)
        datos_frame.pack()

        self._crear_tarjeta_dashboard(datos_frame, "📦 Total de Productos", self.total_productos_var, 0)
        self._crear_tarjeta_dashboard(datos_frame, "⚠️ Bajo Stock (<10)", self.bajo_stock_var, 1)
        self._crear_tarjeta_dashboard(datos_frame, "📂 Categorías Distintas", self.categorias_var, 2)

        self.actualizar_dashboard()

        grafica_frame = ttk.Frame(frame)
        grafica_frame.pack(pady=20)

        self.graficar_pie(grafica_frame)
        self.graficar_barras(grafica_frame)

    def _crear_tarjeta_dashboard(self, parent, titulo, var_texto, columna):
        frame = ttk.LabelFrame(parent, text=titulo, padding=15)
        frame.grid(row=0, column=columna, padx=15, pady=10)
        etiqueta = ttk.Label(frame, textvariable=var_texto, font=("Arial", 20))
        etiqueta.pack()

    def actualizar_dashboard(self):
        self.cargar_productos()
        total = len(self.productos)
        bajo_stock = sum(1 for p in self.productos.values() if int(p["stock"]) < 10)
        categorias = {p["categoria"] for p in self.productos.values()}
        self.total_productos_var.set(str(total))
        self.bajo_stock_var.set(str(bajo_stock))
        self.categorias_var.set(str(len(categorias)))

    def graficar_pie(self, parent):
        conteo = {}
        for p in self.productos.values():
            cat = p["categoria"]
            conteo[cat] = conteo.get(cat, 0) + 1
        if not conteo:
            return
        fig, ax = plt.subplots(figsize=(4, 4))
        ax.pie(conteo.values(), labels=conteo.keys(), autopct="%1.1f%%", startangle=90)
        ax.set_title("Distribución por Categoría")
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.get_tk_widget().grid(row=0, column=0, padx=10)

    def graficar_barras(self, parent):
        nombres = [p["nombre"] for p in self.productos.values()]
        stocks = [int(p["stock"]) for p in self.productos.values()]
        if not nombres:
            return
        fig, ax = plt.subplots(figsize=(4, 4))
        ax.barh(nombres, stocks, color='skyblue')
        ax.set_title("Stock por Producto")
        ax.set_xlabel("Unidades")
        ax.set_ylabel("Producto")
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.get_tk_widget().grid(row=0, column=1, padx=10)

    # -------------------- INVENTARIO --------------------
    def crear_tab_inventario(self):
        ttk.Label(self.content_frame, text="Inventario Actual", font=("Arial", 16)).pack(pady=10)
        tabla = ttk.Treeview(self.content_frame, columns=("Código", "Nombre", "Categoría", "Precio", "Stock"), show="headings")
        for col in tabla["columns"]:
            tabla.heading(col, text=col)
            tabla.column(col, anchor="center", width=150)
        tabla.pack(expand=True, fill="both", padx=10, pady=10)
        for codigo, datos in self.productos.items():
            tabla.insert("", "end", values=(codigo, datos["nombre"], datos["categoria"], datos["precio"], datos["stock"]))
        if self.permiso_usuario in ('admin', 'editor'):
            ttk.Button(self.content_frame, text="Eliminar Producto", command=self.eliminar_producto_ui).pack(pady=5)

    # -------------------- AGREGAR/MODIFICAR PRODUCTO --------------------
    def crear_tab_agregar(self):
        frame = ttk.LabelFrame(self.content_frame, text="Nuevo Producto")
        frame.pack(padx=20, pady=20, fill="x")
        self.entradas = {}
        campos = ["Código", "Nombre", "Categoría", "Precio", "Stock", "Descripción", "Imagen"]
        for i, campo in enumerate(campos):
            ttk.Label(frame, text=campo).grid(row=i, column=0, padx=10, pady=10, sticky="w")
            entrada = ttk.Entry(frame)
            entrada.grid(row=i, column=1, padx=10, pady=10)
            self.entradas[campo.lower()] = entrada
        ttk.Button(frame, text="Agregar Producto", command=self.agregar_producto).grid(row=len(campos), column=0, columnspan=2, pady=15)
        ttk.Button(frame, text="Modificar Producto", command=self.modificar_producto).grid(row=len(campos)+1, column=0, columnspan=2, pady=5)

    def agregar_producto(self):
        datos = {k: v.get() for k, v in self.entradas.items()}
        try:
            datos["precio"] = float(datos["precio"])
            datos["stock"] = int(datos["stock"])
        except ValueError:
            messagebox.showerror("Error", "Precio o stock inválidos.")
            return
        if self.db.agregar_producto(datos):
            messagebox.showinfo("Éxito", "Producto agregado correctamente.")
            self.actualizar_dashboard()
            for entrada in self.entradas.values():
                entrada.delete(0, END)
        else:
            messagebox.showwarning("Advertencia", "Este código ya está registrado o datos inválidos.")

    def modificar_producto(self):
        datos = {k: v.get() for k, v in self.entradas.items()}
        try:
            datos["precio"] = float(datos["precio"])
            datos["stock"] = int(datos["stock"])
        except ValueError:
            messagebox.showerror("Error", "Precio o stock inválidos.")
            return
        if self.db.modificar_producto(datos):
            messagebox.showinfo("Modificado", "Producto modificado correctamente.")
            self.actualizar_dashboard()
            for entrada in self.entradas.values():
                entrada.delete(0, END)
        else:
            messagebox.showerror("Error", "El producto no existe.")

    def eliminar_producto_ui(self):
        win = Toplevel(self.root)
        win.title("Eliminar Producto")
        Label(win, text="Código del producto a eliminar:").pack()
        codigo_entry = Entry(win)
        codigo_entry.pack()
        def eliminar():
            codigo = codigo_entry.get()
            if self.db.eliminar_producto(codigo):
                messagebox.showinfo("Eliminado", "Producto eliminado correctamente.")
                self.actualizar_dashboard()
                win.destroy()
            else:
                messagebox.showerror("Error", "No se pudo eliminar el producto.")
        Button(win, text="Eliminar", command=eliminar).pack()

    # -------------------- BUSCAR PRODUCTO --------------------
    def crear_tab_buscar(self):
        frame = ttk.LabelFrame(self.content_frame, text="Buscar Producto")
        frame.pack(padx=20, pady=20, fill="x")
        ttk.Label(frame, text="Código o Nombre del Producto:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.entrada_busqueda = ttk.Entry(frame)
        self.entrada_busqueda.grid(row=0, column=1, padx=10, pady=10)
        ttk.Button(frame, text="Buscar", command=self.buscar_producto).grid(row=0, column=2, padx=10, pady=10)
        self.resultado_busqueda = Text(self.content_frame, height=6, width=80)
        self.resultado_busqueda.pack(padx=10, pady=10)
        self.imagen_label = None

    def buscar_producto(self):
        entrada = self.entrada_busqueda.get()
        producto = self.db.buscar_producto(entrada)
        self.resultado_busqueda.delete("1.0", END)
        if producto:
            texto = (
                f"Código: {producto['codigo']}\n"
                f"Nombre: {producto['nombre']}\n"
                f"Categoría: {producto['categoria']}\n"
                f"Precio: ${float(producto['precio']):.2f}\n"
                f"Stock: {producto['stock']}\n"
                f"Descripción: {producto.get('descripcion', 'N/A')}"
            )
            self.resultado_busqueda.insert(END, texto)
            if self.imagen_label:
                self.imagen_label.destroy()
            try:
                img = PhotoImage(file=producto['imagen'])
                self.imagen_label = Label(self.content_frame, image=img)
                self.imagen_label.image = img
                self.imagen_label.pack()
            except:
                self.resultado_busqueda.insert(END, "\nImagen no disponible.")
        else:
            self.resultado_busqueda.insert(END, "Producto no encontrado.")

    # -------------------- REALIZAR VENTA --------------------
    def crear_tab_ventas(self):
        frame = ttk.LabelFrame(self.content_frame, text="Nueva Venta")
        frame.pack(padx=20, pady=20, fill="x")
        ttk.Label(frame, text="Código o Nombre del Producto:").grid(row=0, column=0, padx=10, pady=5)
        self.venta_codigo = ttk.Entry(frame)
        self.venta_codigo.grid(row=0, column=1, padx=10, pady=5)
        ttk.Label(frame, text="Cantidad:").grid(row=1, column=0, padx=10, pady=5)
        self.venta_cantidad = ttk.Entry(frame)
        self.venta_cantidad.grid(row=1, column=1, padx=10, pady=5)
        ttk.Button(frame, text="Vender", command=self.realizar_venta).grid(row=2, column=0, columnspan=2, pady=15)

    def realizar_venta(self):
        entrada = self.venta_codigo.get()
        cantidad = self.venta_cantidad.get()
        producto = self.db.buscar_producto(entrada)
        if not producto:
            messagebox.showerror("Error", "Producto no encontrado.")
            return
        try:
            cantidad = int(cantidad)
        except ValueError:
            messagebox.showerror("Error", "Cantidad inválida.")
            return
        if int(producto["stock"]) < cantidad:
            messagebox.showwarning("Advertencia", "Stock insuficiente.")
            return
        producto["stock"] = int(producto["stock"]) - cantidad
        producto_modificado = producto.copy()
        producto_modificado["stock"] = producto["stock"]
        self.db.modificar_producto(producto_modificado)
        total = float(producto["precio"]) * cantidad
        self.historial_ventas.append({
            "codigo": producto["codigo"],
            "nombre": producto["nombre"],
            "cantidad": cantidad,
            "total": total
        })
        messagebox.showinfo("Venta Exitosa", f"Se vendieron {cantidad} unidades.\nTotal: ${total:.2f}")
        self.actualizar_dashboard()

    # -------------------- HISTORIAL DE VENTAS --------------------
    def crear_tab_historial(self):
        ttk.Label(self.content_frame, text="Historial de Ventas", font=("Arial", 16)).pack(pady=10)
        tabla = ttk.Treeview(self.content_frame, columns=("Código", "Nombre", "Cantidad", "Total"), show="headings")
        for col in tabla["columns"]:
            tabla.heading(col, text=col)
            tabla.column(col, anchor="center", width=150)
        tabla.pack(expand=True, fill="both", padx=10, pady=10)
        for venta in self.historial_ventas:
            tabla.insert("", "end", values=(venta["codigo"], venta["nombre"], venta["cantidad"], f"${venta['total']:.2f}"))


# ===== Clase para el login y registro de usuarios =====
class LoginApp:
    def __init__(self):
        self.db = DBConnection()
        self.root = Tk()
        self.root.title('Login')
        self.root.geometry('925x500+300+200')
        self.root.configure(bg="#fff")
        self.root.resizable(False, False)

        try:
            self.img = PhotoImage(file='qw.png')
            Label(self.root, image=self.img, bg='white').place(x=50, y=50)
        except Exception as e:
            print("No se pudo cargar la imagen qw.png:", e)

        self.frame = Frame(self.root, width=350, height=350, bg="white")
        self.frame.place(x=480, y=70)

        Label(self.frame, text='Iniciar Sesión', fg="#020101", bg='white',
              font=('Microsoft YaHei UI Light', 23, 'bold')).place(x=80, y=5)

        self.user = Entry(self.frame, width=25, fg='black', border=0, bg="white",
                          font=('Microsoft YaHei UI Light', 11))
        self.user.place(x=30, y=80)
        self.user.insert(0, 'Nombre de Usuario')
        self.user.bind('<FocusIn>', self.on_enter_user)
        self.user.bind('<FocusOut>', self.on_leave_user)
        Frame(self.frame, width=295, height=2, bg='black').place(x=25, y=107)

        self.code = Entry(self.frame, width=25, fg='black', border=0, bg="white",
                          font=('Microsoft YaHei UI Light', 11))
        self.code.place(x=30, y=150)
        self.code.insert(0, 'Contraseña')
        self.code.bind('<FocusIn>', self.on_enter_code)
        self.code.bind('<FocusOut>', self.on_leave_code)
        Frame(self.frame, width=295, height=2, bg='black').place(x=25, y=177)

        Button(self.frame, width=39, pady=7, text='Iniciar Sesión', bg="#e66d22",
               fg='white', border=0, command=self.iniciar_sesion).place(x=35, y=204)

        Label(self.frame, text="¿No tienes cuenta?", fg='black', bg='white',
              font=('Microsoft YaHei UI Light', 9)).place(x=75, y=270)
        Button(self.frame, width=6, text='Registrar', border=0, bg='white',
               cursor='hand2', fg='#57a1f8', command=self.abrir_registro).place(x=190, y=270)
        self.root.mainloop()

    def on_enter_user(self, e):
        if self.user.get() == 'Nombre de Usuario':
            self.user.delete(0, 'end')

    def on_leave_user(self, e):
        if self.user.get() == '':
            self.user.insert(0, 'Nombre de Usuario')

    def on_enter_code(self, e):
        if self.code.get() == 'Contraseña':
            self.code.delete(0, 'end')
            self.code.config(show='*')

    def on_leave_code(self, e):
        if self.code.get() == '':
            self.code.insert(0, 'Contraseña')
            self.code.config(show='')

    def iniciar_sesion(self):
        usuario = self.user.get()
        contraseña = self.code.get()
        user_data = self.db.verificar_usuario(usuario, contraseña)
        if user_data:
            messagebox.showinfo("Bienvenido", f"Hola {usuario}")
            self.root.destroy()
            root_inventario = Tk()
            app = InventarioApp(root_inventario, self.db, user_data['permiso'])
            root_inventario.mainloop()
        else:
            messagebox.showerror("Error", "Usuario o contraseña incorrectos")

    def abrir_registro(self):
        self.registro_ventana = Toplevel(self.root)
        self.registro_ventana.title("Registrar Nuevo Usuario")
        self.registro_ventana.geometry("400x350")
        self.registro_ventana.config(bg="white")

        Label(self.registro_ventana, text="Registrar Usuario", bg="white", font=('Arial', 14, 'bold')).pack(pady=10)
        Label(self.registro_ventana, text="Nombre de Usuario", bg="white").pack(pady=5)
        self.entry_usuario_reg = Entry(self.registro_ventana)
        self.entry_usuario_reg.pack(pady=5)
        Label(self.registro_ventana, text="Contraseña", bg="white").pack(pady=5)
        self.entry_contra_reg = Entry(self.registro_ventana, show="*")
        self.entry_contra_reg.pack(pady=5)
        Label(self.registro_ventana, text="Permiso (admin/editor/consulta)", bg="white").pack(pady=5)
        self.entry_permiso_reg = Entry(self.registro_ventana)
        self.entry_permiso_reg.pack(pady=5)
        Button(self.registro_ventana, text="Registrar", bg="#fa860b", fg="white", command=self.registrar_usuario).pack(pady=20)

    def registrar_usuario(self):
        usuario = self.entry_usuario_reg.get()
        contra = self.entry_contra_reg.get()
        permiso = self.entry_permiso_reg.get().lower()
        if not usuario or not contra or permiso not in ("admin", "editor", "consulta"):
            messagebox.showwarning("Advertencia", "Completa todos los campos y el permiso debe ser admin, editor o consulta")
            return
        if self.db.registrar_usuario(usuario, contra, permiso):
            messagebox.showinfo("Éxito", "Usuario registrado correctamente")
            self.registro_ventana.destroy()
        else:
            messagebox.showerror("Error", "El usuario ya existe o error en registro")

# ===== Arranca la app =====
if __name__ == "__main__":
    LoginApp()