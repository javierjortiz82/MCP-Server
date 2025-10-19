-- ============================================================================
-- SEED DATA: Products (DML)
-- ============================================================================
-- Total: 90 products
-- Generated from local database (port 5434) using products.json
-- This file contains complete product catalog data for Lab01-MCP
--
-- Executes AFTER: 01_ddl/01_products.sql (table must exist)
-- ============================================================================

-- Disable triggers for faster insertion
ALTER TABLE test.products DISABLE TRIGGER ALL;

-- Clear any existing data (optional - for re-runs)
-- DELETE FROM test.products;

INSERT INTO test.products (sku, name, description, category, brand, tags, color, size, price)
VALUES
('AUD-0001', 'Auriculares Inalámbricos X1', 'Auriculares Bluetooth con cancelación de ruido y 30h de batería.', 'Audio', 'SonicWave', '{audio,auriculares,bluetooth,cancelacion}', 'Negro', 'OneSize', 79.99),
('AUD-0002', 'NoiseBuds Pro', 'True wireless earbuds, touch control, dual mic for calls.', 'Audio', 'ClearSound', '{earbuds,wireless,truewireless}', 'White', 'OneSize', 129.99),
('MOB-0003', 'Protector Vidrio 3D', 'Tempered glass para smartphones, anti-huella.', 'Accesorios', 'GlassGuard', '{screen,protector,vidrio}', 'Transparent', '6.5in', 9.99),
('MOB-0004', 'Cargador Rapido 30W', 'USB-C PD 30W, carga rápida para móviles y tablets.', 'Accesorios', 'ChargeMax', '{charger,usb-c,pd}', 'Black', 'Standard', 19.95),
('TV-0005', 'Smart TV 50" 4K', 'Televisor 4K con HDR y sistema operativo integrado.', 'TV & Video', 'ViewPlus', '{tv,4k,smart}', 'Black', '50inch', 399.0),
('CAM-0006', 'Cámara GoTravel 12MP', 'Compacta para viaje con estabilización óptica.', 'Cámaras', 'TravelCam', '{camera,photography}', 'Silver', 'Compact', 249.0),
('HOME-0007', 'Robot Aspirador S50', 'Aspirador robot con mapeo y control por app.', 'Hogar', 'CleanBot', '{robot,aspirador,hogar}', 'White', 'N/A', 299.99),
('KITCH-0008', 'Licuadora Pro 1200W', 'Potente licuadora con vaso de vidrio.', 'Cocina', 'BlendMaster', '{kitchen,blender}', 'Red', 'Large', 89.5),
('COMP-0009', 'Laptop Ultralight 13"', 'Portátil ultraligero con 16GB RAM y SSD 512GB.', 'Computación', 'ThinBook', '{laptop,ultrabook}', 'Grey', '13inch', 999.0),
('COMP-0010', 'Mouse Ergonómico M500', 'Mouse inalámbrico ergonómico con dpi ajustable.', 'Computación', 'ErgoTech', '{mouse,perifericos}', 'Black', 'Standard', 39.9),
('GAM-0011', 'Silla Gaming XLR', 'Silla con soporte lumbar y reposabrazos ajustable.', 'Gaming', 'ProChair', '{gaming,silla}', 'Negro/Rojo', 'XL', 189.99),
('GAM-0012', 'Teclado Mecánico MK-80', 'Switches táctiles, retroiluminación RGB.', 'Gaming', 'KeyForge', '{keyboard,mechanical}', 'Black', 'Full', 119.0),
('KIDS-0013', 'Set Robótico Educativo', 'Kit para aprender robótica y programación.', 'Educación', 'EduBots', '{robotica,educacion}', 'Multi', 'Set', 59.99),
('SPORT-0014', 'Zapatillas RunFast 2', 'Zapatillas para correr con amortiguación.', 'Deportes', 'RunFast', '{shoes,running}', 'Blue', '42', 89.0),
('OUT-0015', 'Mochila Trek 30L', 'Mochila resistente al agua para trekking.', 'Outdoor', 'TrailPro', '{mochila,trekking}', 'Green', '30L', 69.99),
('AUTO-0016', 'GPS Navigator 7"', 'Navegador para auto con mapas offline.', 'Automotriz', 'NavRoad', '{gps,auto}', 'Black', '7inch', 129.99),
('BEAU-0017', 'Secador Profesional 2000W', 'Secador con ajuste de temperatura y frío.', 'Belleza', 'StylePro', '{hair,dryer}', 'Black', 'Standard', 49.9),
('TOY-0018', 'Puzzle 1000 Piezas - Mundo', 'Rompecabezas para adultos con piezas de calidad.', 'Juguetes', 'PuzzleArt', '{puzzle,juego}', 'Multi', '1000pcs', 24.5),
('OFF-0019', 'Escritorio Ajustable', 'Escritorio standing con altura ajustable eléctrico.', 'Oficina', 'ErgoDesk', '{desk,standing}', 'White', '120x60', 259.0),
('OFF-0020', 'Silla Oficina Comfort', 'Silla con soporte lumbar y asiento acolchado.', 'Oficina', 'OfficeEase', '{office,silla}', 'Grey', 'Standard', 149.99),
('PET-0021', 'Correa para Perros - Nylon', 'Correa resistente y cómoda para paseos diarios.', 'Mascotas', 'PetWalk', '{pet,correa}', 'Blue', 'M', 12.99),
('HEAL-0022', 'Monitor de Presión MX2', 'Tensiómetro digital con memoria para 2 usuarios.', 'Salud', 'HealthTrack', '{salud,monitor}', 'White', 'OneSize', 39.5),
('TOOL-0023', 'Taladro Inalámbrico 18V', 'Taladro con batería de larga duración y maletín.', 'Herramientas', 'PowerDrill', '{taladro,herramientas}', 'Yellow', 'Standard', 79.0),
('KITCH-0024', 'Set de Cuchillos 6 Piezas', 'Cuchillos de acero inoxidable con bloque de madera.', 'Cocina', 'ChefLine', '{cuchillos,kitchen}', 'Wood', '6pcs', 59.99),
('BED-0025', 'Almohada Memory Foam', 'Almohada ortopédica con memoria de forma.', 'Hogar', 'SleepWell', '{almohada,dormir}', 'White', 'Standard', 45.0),
('FASH-0026', 'Reloj SmartFit', 'Smartwatch con monitor de frecuencia y notificaciones.', 'Ropa & Accesorios', 'TimeTech', '{smartwatch,wearable}', 'Black', 'OneSize', 129.99),
('MUS-0027', 'Teclado MIDI 49', 'Controlador MIDI para producción musical.', 'Música', 'TuneMaster', '{midi,musica}', 'Black', '49keys', 199.0),
('PHOTO-0028', 'Tripode Aluminio 1.8m', 'Trípode ligero y resistente para cámaras.', 'Cámaras', 'SteadyShot', '{tripod,camera}', 'Black', '1.8m', 49.0),
('GAM-0029', 'Auriculares Gaming GH-1', 'Auriculares con micrófono y sonido 7.1 virtual.', 'Gaming', 'GameBeat', '{gaming,auriculares}', 'Black', 'OneSize', 79.99),
('BED-0030', 'Cobija Termica 220x240', 'Cobija de microfibra, térmica y suave.', 'Hogar', 'WarmHome', '{cobija,hogar}', 'Grey', '220x240', 39.9),
('AUTO-0031', 'Cargador Auto Dual USB', 'Cargador para auto con 2 puertos USB.', 'Automotriz', 'AutoCharge', '{auto,charger}', 'Black', 'Standard', 14.99),
('SPORT-0032', 'Balón Futbol Pro', 'Balón oficial para entrenamiento y partidos.', 'Deportes', 'SportPro', '{futbol,balon}', 'White', '5', 29.99),
('BEAU-0033', 'Set Manicura Profesional', 'Kit de manicura con herramientas de acero.', 'Belleza', 'NailPro', '{manicura,belleza}', 'Pink', 'Set', 24.99),
('TOY-0034', 'Drone Mini 4K', 'Drone con cámara 4K y control por app.', 'Juguetes', 'SkyCam', '{drone,camera}', 'White', 'Mini', 189.0),
('HOME-0035', 'Humidificador Ultrasónico', 'Humidificador con temporizador y luz LED.', 'Hogar', 'AirCare', '{humidificador,hogar}', 'White', '500ml', 34.99),
('GARD-0036', 'Tijeras Electricas 7V', 'Tijeras para jardín recargables.', 'Jardín', 'GardenPro', '{jardin,tijeras}', 'Green', 'Small', 49.0),
('COM-0037', 'Switch Ethernet 8 Puertos', 'Switch gigabit con 8 puertos para oficina.', 'Redes', 'NetGear', '{network,switch}', 'Black', '8port', 59.99),
('COMP-0038', 'SSD NVMe 1TB', 'Unidad NVMe con altas tasas de lectura/escritura.', 'Computación', 'FastDrive', '{ssd,nvme}', 'N/A', '1TB', 119.99),
('AUD-0039', 'Barra Sonido 2.1', 'Barra de sonido con subwoofer y bluetooth.', 'Audio', 'HomeSound', '{soundbar,audio}', 'Black', '100cm', 149.0),
('SPORT-0040', 'Bicicleta Plegable', 'Bicicleta con cuadro plegable ideal para ciudad.', 'Transporte', 'FoldBike', '{bici,plegable}', 'Black', 'M', 349.99),
('FASH-0041', 'Chaqueta Impermeable', 'Chaqueta con membrana impermeable y capucha.', 'Ropa & Accesorios', 'RainShield', '{chaqueta,impermeable}', 'Blue', 'L', 99.0),
('PET-0042', 'Cama Mascota Deluxe', 'Cama acolchada con funda lavable.', 'Mascotas', 'PetComfort', '{cama,pet}', 'Grey', 'Large', 39.0),
('HOME-0043', 'Lámpara LED Smart', 'Lámpara con wifi y control por app.', 'Hogar', 'BrightHome', '{lampara,smart}', 'White', 'Standard', 29.99),
('KITCH-0044', 'Sartén Antiadherente 28cm', 'Sartén con revestimiento cerámico.', 'Cocina', 'CookPro', '{sarten,cocina}', 'Black', '28cm', 25.0),
('BEAU-0045', 'Perfume Ocean Breeze 100ml', 'Fragancia fresca para uso diario.', 'Belleza', 'AquaScent', '{perfume,fragancia}', 'Transparent', '100ml', 49.99),
('TOOL-0046', 'Llave Inglesa Ajustable 12"', 'Herramienta resistente para taller.', 'Herramientas', 'ToolWorks', '{herramientas,llave}', 'Silver', '12inch', 14.5),
('AUTO-0047', 'Cámara Reversa HD', 'Cámara para retrovisor con visión nocturna.', 'Automotriz', 'RearView', '{camara,auto}', 'Black', 'OneSize', 59.99),
('COM-0048', 'UPS 1000VA', 'Suministro ininterrumpido para equipos de oficina.', 'Redes', 'PowerSafe', '{ups,energia}', 'Black', '1000VA', 129.0),
('MUS-0049', 'Auriculares Estudio S-80', 'Auriculares de monitoreo para estudio.', 'Música', 'StudioPro', '{auriculares,estudio}', 'Black', 'OneSize', 129.0),
('FASH-0050', 'Bolso Cuero Vintage', 'Bolso de cuero genuino estilo vintage.', 'Ropa & Accesorios', 'LeatherCraft', '{bolso,cuero}', 'Brown', 'M', 149.0),
('COMP-0051', 'Laptop Gaming ASUS ROG Strix G16', 'Intel Core i9-14900HX, NVIDIA RTX 4070 8GB, 32GB DDR5 RAM, 1TB NVMe SSD, pantalla 16" QHD 240Hz.', 'Computación', 'ASUS', '{laptop,gaming,rog,rtx}', 'Black', '16inch', 1799.99),
('COMP-0052', 'Laptop Gaming MSI Katana 15', 'Intel Core i7-13620H, NVIDIA RTX 4050 6GB, 16GB DDR5, 512GB SSD, 15.6" FHD 144Hz.', 'Computación', 'MSI', '{laptop,gaming,katana,msi}', 'Black', '15.6inch', 999.99),
('COMP-0053', 'Laptop Gaming Lenovo Legion Pro 5i', 'Intel Core i7-14650HX, NVIDIA RTX 4060 8GB, 16GB DDR5, 1TB SSD, 16" QHD+ 165Hz G-Sync.', 'Computación', 'Lenovo', '{laptop,gaming,legion,nvidia}', 'Grey', '16inch', 1313.99),
('COMP-0054', 'Laptop Gaming Acer Nitro 5', 'AMD Ryzen 7 7735HS, NVIDIA RTX 4050 6GB, 16GB DDR5, 512GB NVMe, pantalla 15.6" FHD 144Hz.', 'Computación', 'Acer', '{laptop,gaming,nitro,amd}', 'Black', '15.6inch', 899.99),
('COMP-0055', 'Laptop Gaming HP Victus 15', 'AMD Ryzen 5 7535HS, NVIDIA RTX 2050 4GB, 16GB DDR5, 512GB SSD, 15.6" FHD 60Hz.', 'Computación', 'HP', '{laptop,gaming,victus,budget}', 'Black', '15.6inch', 699.99),
('COMP-0056', 'Laptop Gaming Dell G16 7630', 'Intel Core i7-13650HX, NVIDIA RTX 4060 8GB, 16GB DDR5, 1TB SSD, 16" QHD+ 165Hz.', 'Computación', 'Dell', '{laptop,gaming,dell,g16}', 'Black', '16inch', 999.0),
('COMP-0057', 'Laptop Gaming MSI Raider GE78', 'Intel Core i9-14900HX, NVIDIA RTX 4080 12GB, 32GB DDR5, 2TB NVMe, 17" 4K 144Hz Mini LED.', 'Computación', 'MSI', '{laptop,gaming,raider,premium}', 'Black', '17.3inch', 2499.99),
('COMP-0058', 'Laptop Gaming ASUS TUF A15', 'AMD Ryzen 7 8845HS, NVIDIA RTX 4070 8GB, 32GB DDR5, 1TB SSD, 15.6" FHD 144Hz.', 'Computación', 'ASUS', '{laptop,gaming,tuf,amd}', 'Grey', '15.6inch', 1299.99),
('COMP-0059', 'Laptop Gaming Acer Predator Helios 300', 'Intel Core i7-13700H, NVIDIA RTX 4060 8GB, 16GB DDR5, 1TB NVMe, 15.6" QHD 165Hz.', 'Computación', 'Acer', '{laptop,gaming,predator,intel}', 'Black', '15.6inch', 1399.99),
('COMP-0060', 'Laptop Gaming HP OMEN 16', 'Intel Core i7-13700HX, NVIDIA RTX 4070 8GB, 32GB DDR5, 1TB SSD, 16.1" QHD 165Hz.', 'Computación', 'HP', '{laptop,gaming,omen,hp}', 'Black', '16inch', 1499.99),
('COMP-0061', 'Laptop Gaming Dell Alienware m15 R7', 'Intel Core i9-12900H, NVIDIA RTX 4070 8GB, 32GB DDR5, 1TB NVMe, 15.6" QHD 240Hz.', 'Computación', 'Dell', '{laptop,gaming,alienware,premium}', 'White', '15.6inch', 1799.99),
('COMP-0062', 'Laptop Gaming Lenovo Legion 5', 'AMD Ryzen 5 7640HS, NVIDIA RTX 4050 6GB, 16GB DDR5, 512GB SSD, 15.6" FHD 144Hz.', 'Computación', 'Lenovo', '{laptop,gaming,legion,budget}', 'Grey', '15.6inch', 849.99),
('COMP-0063', 'MacBook Air M4 13"', 'Apple M4 chip 8-core CPU, 10-core GPU, 16GB unified memory, 512GB SSD, 13.6" Liquid Retina.', 'Computación', 'Apple', '{laptop,macbook,ultrabook,m4}', 'Silver', '13inch', 1499.0),
('COMP-0064', 'Dell XPS 13 Plus', 'Intel Core i7-1360P, Intel Iris Xe, 16GB LPDDR5, 512GB SSD, 13.4" FHD+ touchscreen.', 'Computación', 'Dell', '{laptop,ultrabook,xps,premium}', 'Silver', '13inch', 1399.99),
('COMP-0065', 'HP Spectre x360 14', 'Intel Core i7-1355U, Intel Iris Xe, 16GB LPDDR4x, 1TB SSD, 13.5" WUXGA+ OLED touch, convertible.', 'Computación', 'HP', '{laptop,ultrabook,2in1,spectre}', 'Blue', '14inch', 1599.99),
('COMP-0066', 'ASUS ZenBook 14 OLED', 'Intel Core i5-1340P, Intel Iris Xe, 16GB LPDDR5, 512GB SSD, 14" 2.8K OLED touchscreen.', 'Computación', 'ASUS', '{laptop,ultrabook,zenbook,oled}', 'Grey', '14inch', 899.99),
('COMP-0067', 'Lenovo Yoga 9i Gen 9', 'Intel Core Ultra 7 258V, 32GB LPDDR5x, 1TB SSD, 14" 4K OLED touch, convertible 2-in-1.', 'Computación', 'Lenovo', '{laptop,ultrabook,yoga,2in1}', 'Grey', '14inch', 1499.99),
('COMP-0068', 'Dell XPS 15 9530', 'Intel Core i7-13700H, NVIDIA RTX 4050 6GB, 16GB DDR5, 512GB SSD, 15.6" FHD+ non-touch.', 'Computación', 'Dell', '{laptop,ultrabook,xps,creator}', 'Silver', '15.6inch', 1699.99),
('COMP-0069', 'MacBook Pro 14" M4 Pro', 'Apple M4 Pro chip 12-core CPU, 18-core GPU, 24GB unified memory, 1TB SSD, 14.2" Liquid Retina XDR.', 'Computación', 'Apple', '{laptop,macbook,pro,m4pro}', 'Space Grey', '14inch', 2299.0),
('COMP-0070', 'HP Envy 13', 'Intel Core i5-1335U, Intel Iris Xe, 8GB LPDDR4x, 256GB SSD, 13.3" FHD IPS, ultraportátil.', 'Computación', 'HP', '{laptop,ultrabook,envy,portátil}', 'Silver', '13inch', 799.99),
('COMP-0071', 'Lenovo ThinkPad X1 Carbon Gen 12', 'Intel Core i7-1365U vPro, 16GB LPDDR5, 512GB SSD, 14" WUXGA IPS, teclado retroiluminado.', 'Computación', 'Lenovo', '{laptop,thinkpad,business,ultrabook}', 'Black', '14inch', 1599.99),
('COMP-0072', 'Lenovo ThinkPad T14 Gen 4', 'AMD Ryzen 7 PRO 7840U, 16GB DDR5, 512GB SSD, 14" WUXGA IPS, Windows 11 Pro.', 'Computación', 'Lenovo', '{laptop,thinkpad,business,oficina}', 'Black', '14inch', 1199.99),
('COMP-0073', 'HP ProBook 450 G10', 'Intel Core i5-1335U, 8GB DDR4, 256GB SSD, 15.6" FHD IPS, Windows 11 Pro, durabilidad militar.', 'Computación', 'HP', '{laptop,probook,business,oficina}', 'Silver', '15.6inch', 849.99),
('COMP-0074', 'Dell Latitude 5540', 'Intel Core i7-1365U vPro, 16GB DDR4, 512GB SSD, 15.6" FHD, Windows 11 Pro, business laptop.', 'Computación', 'Dell', '{laptop,latitude,business,dell}', 'Grey', '15.6inch', 1299.99),
('COMP-0075', 'ASUS ExpertBook B9', 'Intel Core i7-1355U, 16GB LPDDR5, 1TB SSD, 14" FHD, ultra-ligera 990g, 12h batería.', 'Computación', 'ASUS', '{laptop,expertbook,business,ultraligera}', 'Black', '14inch', 1399.99),
('COMP-0076', 'HP EliteBook 840 G10', 'Intel Core i5-1340P, 16GB DDR5, 512GB SSD, 14" WUXGA, Windows 11 Pro, seguridad empresarial.', 'Computación', 'HP', '{laptop,elitebook,business,premium}', 'Silver', '14inch', 1149.99),
('COMP-0077', 'Lenovo ThinkPad P15v Gen 3', 'Intel Core i7-12700H, NVIDIA RTX A2000 8GB, 32GB DDR5, 1TB SSD, 15.6" FHD IPS, workstation.', 'Computación', 'Lenovo', '{laptop,thinkpad,workstation,profesional}', 'Black', '15.6inch', 1899.99),
('COMP-0078', 'Dell Precision 3571', 'Intel Core i7-12850HX, NVIDIA RTX A1000 4GB, 32GB DDR5, 512GB SSD, 15.6" FHD, ISV certified.', 'Computación', 'Dell', '{laptop,precision,workstation,cad}', 'Grey', '15.6inch', 1799.99),
('COMP-0079', 'HP ZBook Firefly 14 G10', 'Intel Core i7-1355U, NVIDIA RTX A500 4GB, 16GB DDR5, 512GB SSD, 14" FHD, ultraportable workstation.', 'Computación', 'HP', '{laptop,zbook,workstation,diseño}', 'Silver', '14inch', 1599.99),
('COMP-0080', 'ASUS ProArt StudioBook 16', 'Intel Core i9-13980HX, NVIDIA RTX 4070 8GB, 64GB DDR5, 2TB SSD, 16" 3.2K OLED, content creation.', 'Computación', 'ASUS', '{laptop,proart,workstation,creator}', 'Black', '16inch', 2399.99),
('COMP-0081', 'HP Pavilion 15', 'Intel Core i5-1235U, Intel Iris Xe, 8GB DDR4, 256GB SSD, 15.6" FHD IPS, laptop versátil estudiantes.', 'Computación', 'HP', '{laptop,pavilion,estudiantes,economica}', 'Silver', '15.6inch', 579.99),
('COMP-0082', 'Lenovo IdeaPad 3 15', 'AMD Ryzen 5 7530U, 8GB DDR4, 256GB SSD, 15.6" FHD TN, uso diario y estudio.', 'Computación', 'Lenovo', '{laptop,ideapad,estudiantes,budget}', 'Grey', '15.6inch', 479.99),
('COMP-0083', 'Acer Swift 3', 'Intel Core i5-1240P, Intel Iris Xe, 8GB LPDDR4x, 512GB SSD, 14" FHD IPS, ultradelgada estudiantes.', 'Computación', 'Acer', '{laptop,swift,estudiantes,ultrabook}', 'Silver', '14inch', 649.99),
('COMP-0084', 'ASUS VivoBook 15', 'Intel Core i3-1215U, Intel UHD Graphics, 8GB DDR4, 256GB SSD, 15.6" FHD, laptop básica.', 'Computación', 'ASUS', '{laptop,vivobook,basica,economica}', 'Blue', '15.6inch', 499.99),
('COMP-0085', 'HP Pavilion x360 14', 'Intel Core i5-1335U, Intel Iris Xe, 8GB DDR4, 256GB SSD, 14" FHD touch, convertible 2-in-1 estudiantes.', 'Computación', 'HP', '{laptop,pavilion,2in1,estudiantes}', 'Silver', '14inch', 699.99),
('COMP-0086', 'Lenovo IdeaPad Flex 5', 'AMD Ryzen 5 7530U, 16GB DDR4, 512GB SSD, 14" FHD touch, convertible multitarea.', 'Computación', 'Lenovo', '{laptop,ideapad,2in1,flex}', 'Grey', '14inch', 629.99),
('COMP-0087', 'Acer Aspire 5', 'Intel Core i5-1235U, Intel Iris Xe, 8GB DDR4, 512GB SSD, 15.6" FHD IPS, laptop multimedia.', 'Computación', 'Acer', '{laptop,aspire,multimedia,estudiantes}', 'Silver', '15.6inch', 599.99),
('COMP-0088', 'ASUS Chromebook Flip CX5', 'Intel Core i5-1135G7, 8GB LPDDR4x, 256GB eMMC, 15.6" FHD touch, Chrome OS, convertible.', 'Computación', 'ASUS', '{laptop,chromebook,2in1,chrome}', 'Grey', '15.6inch', 549.99),
('COMP-0089', 'Dell Inspiron 15 3520', 'Intel Core i3-1215U, Intel UHD Graphics, 8GB DDR4, 256GB SSD, 15.6" FHD, laptop básica oficina.', 'Computación', 'Dell', '{laptop,inspiron,basica,oficina}', 'Black', '15.6inch', 499.99),
('COMP-0090', 'Lenovo V15 Gen 4', 'AMD Ryzen 3 7320U, 8GB DDR4, 256GB SSD, 15.6" FHD TN, laptop económica uso básico.', 'Computación', 'Lenovo', '{laptop,v15,economica,basica}', 'Black', '15.6inch', 449.99);

-- Re-enable triggers
ALTER TABLE test.products ENABLE TRIGGER ALL;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
-- Expected: 90 products inserted into test.products table
-- Run the following query to verify:
-- SELECT COUNT(*) as total_products, COUNT(DISTINCT category) as categories FROM test.products;
-- Should return: 90 products across 23 categories
-- ============================================================================
