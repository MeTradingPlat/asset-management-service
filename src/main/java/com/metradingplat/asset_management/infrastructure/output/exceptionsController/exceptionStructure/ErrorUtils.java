package com.metradingplat.asset_management.infrastructure.output.exceptionsController.exceptionStructure;

public final class ErrorUtils {

    ErrorUtils() {
    }

    public static Error crearError(final String codigoError,
            final String llaveMensaje,
            final Integer codigoHttp,
            final String url,
            final String metodo) {
        final Error error = new Error();
        error.setCodigoError(codigoError);
        error.setMensaje(llaveMensaje);
        error.setCodigoHttp(codigoHttp);
        error.setUrl(url);
        error.setMetodo(metodo);
        return error;
    }
}
