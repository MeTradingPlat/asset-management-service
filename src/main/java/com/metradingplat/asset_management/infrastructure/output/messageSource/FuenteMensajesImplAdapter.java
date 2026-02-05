package com.metradingplat.asset_management.infrastructure.output.messageSource;

import java.text.MessageFormat;
import java.util.Locale;

import org.springframework.context.MessageSource;
import org.springframework.context.i18n.LocaleContextHolder;
import org.springframework.stereotype.Component;

import lombok.RequiredArgsConstructor;

import com.metradingplat.asset_management.application.output.FuenteMensajesIntPort;

@Component
@RequiredArgsConstructor
public class FuenteMensajesImplAdapter implements FuenteMensajesIntPort {

    private final MessageSource messageSource;

    @Override
    public String obtenerMensaje(String llaveMensaje, Locale locale, Object... args) {
        String pattern = this.messageSource.getMessage(llaveMensaje, null, locale);
        return (args != null && args.length > 0)
                ? MessageFormat.format(pattern, args)
                : pattern;
    }

    private Locale getLocale() {
        return LocaleContextHolder.getLocale();
    }

    @Override
    public String internacionalizarMensaje(String llaveMensaje, Object... args) {
        return this.obtenerMensaje(llaveMensaje, this.getLocale(), args);
    }
}
