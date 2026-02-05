package com.metradingplat.asset_management.infrastructure.output.formatter;

import org.springframework.stereotype.Component;

import com.metradingplat.asset_management.application.output.FormateadorResultadosIntPort;
import com.metradingplat.asset_management.infrastructure.output.exceptionsController.ownExceptions.EntidadNoExisteException;
import com.metradingplat.asset_management.infrastructure.output.exceptionsController.ownExceptions.EntidadYaExisteException;
import com.metradingplat.asset_management.infrastructure.output.exceptionsController.ownExceptions.ReglaNegocioException;

@Component
public class FormateadorResultadosImplAdapter implements FormateadorResultadosIntPort {

    @Override
    public void errorEntidadYaExiste(String llaveMensaje, Object... args) {
        throw new EntidadYaExisteException(llaveMensaje, args);
    }

    @Override
    public void errorEntidadNoExiste(String llaveMensaje, Object... args) {
        throw new EntidadNoExisteException(llaveMensaje, args);
    }

    @Override
    public void errorReglaNegocioViolada(String llaveMensaje, Object... args) {
        throw new ReglaNegocioException(llaveMensaje, args);
    }
}
