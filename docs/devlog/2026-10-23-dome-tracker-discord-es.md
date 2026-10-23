**Dome tracker, parte 1: R2 te mira**

El objetivo a largo plazo es un droide que se mueva solo por una habitación o que te siga en un evento. Para llegar ahí voy por pasos, de lo más simple a lo más complejo. Primer paso: **que el dome te mire** y te siga con la cabeza mientras te mueves a su alrededor.

**Cómo funciona:** una cámara en el dome busca la cara más cercana. Si está a la derecha del centro de la imagen, el dome gira a la derecha; si está centrada, se para. Como la cámara gira con la cabeza, no hace falta sensor de posición del dome. El "cerebro" es una **Raspberry Pi 4** junto a la Mega ADK, conectada por USB.

**En el firmware**, un solo comando nuevo en ShadowMD Lite: `DM:<velocidad>` mueve el dome.
- Si deja de llegar durante 300 ms, el dome se para.
- **El stick del PS3 Nav siempre manda.** Si mueves el dome a mano, el seguimiento se ignora 2 segundos.
- Va detrás de un `#define`: desactivado, el sketch queda como estaba.

**La primera prueba** fue con una webcam pegada con cinta al dome y el portátil. Me detectaba a la primera... y el dome se iba en dirección contraria. Dos culpables:
- las teclas no llegaban a la ventana del vídeo, así que "invertir" nunca se activó;
- el dome giraba tan rápido que se pasaba de largo, me perdía y volvía. Visto desde delante, parecía que me esquivaba.

**Para que siga a un ritmo natural**, el control mira también hacia dónde se mueve tu cara: si te alejas del centro acelera, y si ya vuelve al centro frena antes de llegar. Con eso la velocidad máxima pasó de 28 a 58 sin pasarse.

**Si te pierde**, a los 1,5 s vuelve al frente. Sin sensor, sabe cuánto ha girado midiendo cuánto se desplaza la habitación en la imagen. Esto aún hay que probarlo más.

**En la Raspberry Pi 4** al principio iba a 10 fps. Detectando sobre una imagen más pequeña (320×240) va a **25 fps**, igual que el portátil. Además:
- arranca sola al encender;
- espera a la Mega si la conectas más tarde;
- muestra en el monitor por HDMI, y en el móvil por WiFi, una página con el **logo de Astromech Spain** y la imagen de la cámara en directo.

**Estado:** probado en el droide. El dome me sigue a izquierda y derecha, todo desde la Pi y con el Nav al mando. El límite es el cable de la webcam en el dome.

**Lo siguiente:**
- una cámara inalámbrica en el dome (ESP32-S3 con cámara de 120°, alimentada con los 12 V del slip ring);
- un sensor de ángulo del dome;
- después, que el droide entero te siga.

El código todavía no es público; pondré los enlaces cuando lo sea.
