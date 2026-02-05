package com.metradingplat.asset_management.application.output;

public interface FormateadorResultadosIntPort {
    void errorEntidadYaExiste(String llaveMensaje, Object... args);

    void errorEntidadNoExiste(String llaveMensaje, Object... args);

    void errorReglaNegocioViolada(String llaveMensaje, Object... args);
}
