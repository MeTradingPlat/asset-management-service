package com.metradingplat.asset_management.infrastructure.configuration;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import com.metradingplat.asset_management.application.output.FormateadorResultadosIntPort;
import com.metradingplat.asset_management.application.output.GestionarActivoGatewayIntPort;
import com.metradingplat.asset_management.domain.usecases.GestionarActivoCUAdapter;

@Configuration
public class BeanConfigurations {

    @Bean
    public GestionarActivoCUAdapter gestionarActivoCUIntPort(
            GestionarActivoGatewayIntPort objGestionarActivoGatewayIntPort,
            FormateadorResultadosIntPort objFormateadorResultadosIntPort) {
        return new GestionarActivoCUAdapter(objGestionarActivoGatewayIntPort, objFormateadorResultadosIntPort);
    }
}
