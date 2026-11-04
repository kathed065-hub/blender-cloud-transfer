FROM blenderkit/headless-blender:blender-4.2-stable
USER root
RUN mkdir -p /seed
COPY ["solo malla.glb", "/seed/solo_malla.glb"]
COPY seed_model.py /seed/seed_model.py
