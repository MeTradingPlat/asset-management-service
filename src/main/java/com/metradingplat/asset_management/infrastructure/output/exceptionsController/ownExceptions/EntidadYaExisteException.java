package com.metradingplat.asset_management.infrastructure.output.exceptionsController.ownExceptions;

import com.metradingplat.asset_management.infrastructure.output.exceptionsController.exceptionStructure.CodigoError;

public class EntidadYaExisteException extends BaseException {
    public EntidadYaExisteException(String llaveMensaje, Object... args) {
        super(CodigoError.ENTIDAD_YA_EXISTE, llaveMensaje, args);
    }
}
