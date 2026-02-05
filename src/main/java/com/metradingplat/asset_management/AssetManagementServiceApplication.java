package com.metradingplat.asset_management;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;

@SpringBootApplication
@EnableDiscoveryClient
public class AssetManagementServiceApplication {

	public static void main(String[] args) {
		SpringApplication.run(AssetManagementServiceApplication.class, args);
	}

}
