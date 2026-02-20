package com.metradingplat.asset_management.infrastructure.configuration;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.support.converter.RecordMessageConverter;
import org.springframework.kafka.support.converter.StringJsonMessageConverter;

@Configuration
public class KafkaConsumerConfig {

    @Bean
    public RecordMessageConverter kafkaMessageConverter() {
        return new StringJsonMessageConverter();
    }
}
