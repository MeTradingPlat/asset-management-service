package com.metradingplat.asset_management.infrastructure.input;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;

import org.springframework.lang.NonNull;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import com.metradingplat.asset_management.application.output.FuenteMensajesIntPort;

import java.io.IOException;

@Component
@RequiredArgsConstructor
public class GatewayHeaderFilter extends OncePerRequestFilter {

    private final FuenteMensajesIntPort objFuenteMensajes;

    @Override
    protected void doFilterInternal(@NonNull HttpServletRequest request, @NonNull HttpServletResponse response,
            @NonNull FilterChain filterChain)
            throws ServletException, IOException {

        String path = request.getRequestURI();
        if (path.startsWith("/actuator") || path.startsWith("/eureka")) {
            filterChain.doFilter(request, response);
            return;
        }

        String header = request.getHeader("X-Gateway-Passed");

        if (header == null || !header.equals("true")) {
            String mensaje = this.objFuenteMensajes.internacionalizarMensaje("error.access.denied");
            response.sendError(HttpServletResponse.SC_FORBIDDEN, mensaje);
            return;
        }

        filterChain.doFilter(request, response);
    }
}
