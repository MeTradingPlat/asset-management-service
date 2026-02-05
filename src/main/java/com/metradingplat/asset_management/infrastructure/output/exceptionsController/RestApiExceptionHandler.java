package com.metradingplat.asset_management.infrastructure.output.exceptionsController;

import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;

import com.metradingplat.asset_management.application.output.FuenteMensajesIntPort;
import com.metradingplat.asset_management.infrastructure.output.exceptionsController.exceptionStructure.CodigoError;
import com.metradingplat.asset_management.infrastructure.output.exceptionsController.exceptionStructure.Error;
import com.metradingplat.asset_management.infrastructure.output.exceptionsController.exceptionStructure.ErrorUtils;
import com.metradingplat.asset_management.infrastructure.output.exceptionsController.ownExceptions.*;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.validation.FieldError;

import java.util.HashMap;
import java.util.Map;

@RestControllerAdvice
@RequiredArgsConstructor
public class RestApiExceptionHandler {

    private final FuenteMensajesIntPort objFuenteMensajes;

    @ExceptionHandler(Exception.class)
    public ResponseEntity<Error> handleGenericException(HttpServletRequest req, Exception ex) {
        return createErrorResponse(
                CodigoError.ERROR_GENERICO,
                HttpStatus.INTERNAL_SERVER_ERROR,
                req,
                CodigoError.ERROR_GENERICO.getLlaveMensaje());
    }

    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    public ResponseEntity<Error> handleTypeMismatch(MethodArgumentTypeMismatchException ex, HttpServletRequest req) {
        return createErrorResponse(
                CodigoError.TIPO_DE_ARGUMENTO_INVALIDO,
                HttpStatus.BAD_REQUEST,
                req,
                CodigoError.TIPO_DE_ARGUMENTO_INVALIDO.getLlaveMensaje());
    }

    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ResponseEntity<Error> handleHttpMessageNotReadable(HttpMessageNotReadableException ex,
            HttpServletRequest req) {
        String errorMessage = internacionalizarMensaje("error.formato.datos.invalido");
        Error error = ErrorUtils.crearError(
                CodigoError.VIOLACION_REGLA_DE_NEGOCIO.getCodigo(),
                errorMessage,
                HttpStatus.BAD_REQUEST.value(),
                req.getRequestURL().toString(),
                req.getMethod());
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(error);
    }

    @ExceptionHandler(EntidadYaExisteException.class)
    public ResponseEntity<Error> handleEntidadYaExisteException(final HttpServletRequest req,
            final EntidadYaExisteException ex) {
        return createErrorResponse(
                CodigoError.ENTIDAD_YA_EXISTE,
                HttpStatus.NOT_ACCEPTABLE,
                req,
                ex.getMessage(),
                ex.getArgs());
    }

    @ExceptionHandler(EntidadNoExisteException.class)
    public ResponseEntity<Error> handleEntidadNoExisteException(EntidadNoExisteException ex, HttpServletRequest req) {
        return createErrorResponse(
                CodigoError.ENTIDAD_NO_ENCONTRADA,
                HttpStatus.NOT_ACCEPTABLE,
                req,
                ex.getMessage(),
                ex.getArgs());
    }

    @ExceptionHandler(ReglaNegocioException.class)
    public ResponseEntity<Error> handleReglaNegocioExcepcion(ReglaNegocioException ex, HttpServletRequest req) {
        return createErrorResponse(
                CodigoError.VIOLACION_REGLA_DE_NEGOCIO,
                HttpStatus.BAD_REQUEST,
                req,
                ex.getMessage(),
                ex.getArgs());
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<Error> handleValidationExceptions(MethodArgumentNotValidException ex,
            HttpServletRequest req) {
        StringBuilder mensajeCompleto = new StringBuilder();
        Map<String, String> erroresDetallados = new HashMap<>();

        ex.getBindingResult().getAllErrors().forEach(error -> {
            String campo = (error instanceof FieldError) ? ((FieldError) error).getField()
                    : error.getObjectName();

            Object[] args = error.getArguments();
            Object[] processedArgs = null;
            if (args != null && args.length > 1) {
                processedArgs = new Object[args.length - 1];
                int targetIndex = 0;
                for (int i = 1; i < args.length; i++) {
                    processedArgs[targetIndex++] = args[i];
                }
            }

            String mensajeDeError = internacionalizarMensaje(error.getDefaultMessage(), processedArgs);
            erroresDetallados.put(campo, mensajeDeError);

            if (mensajeCompleto.length() > 0) {
                mensajeCompleto.append("; ");
            }
            mensajeCompleto.append(campo).append(": ").append(mensajeDeError);
        });

        Error error = ErrorUtils.crearError(
                CodigoError.VIOLACION_REGLA_DE_NEGOCIO.getCodigo(),
                mensajeCompleto.toString(),
                HttpStatus.BAD_REQUEST.value(),
                req.getRequestURL().toString(),
                req.getMethod());

        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(error);
    }

    private ResponseEntity<Error> createErrorResponse(CodigoError codigoError, HttpStatus httpStatus,
            HttpServletRequest req, String mensajeClave, Object... args) {
        String mensaje = internacionalizarMensaje(mensajeClave, args);
        Error error = ErrorUtils.crearError(
                codigoError.getCodigo(),
                mensaje,
                httpStatus.value(),
                req.getRequestURL().toString(),
                req.getMethod());
        return ResponseEntity.status(httpStatus).body(error);
    }

    private String internacionalizarMensaje(String claveMensaje, Object... args) {
        Object[] argumentos = (args == null || args.length == 0) ? new Object[] {} : args;
        return this.objFuenteMensajes.internacionalizarMensaje(claveMensaje, argumentos);
    }
}
