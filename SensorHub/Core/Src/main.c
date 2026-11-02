/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.c
  * @brief          : Main program body
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2026 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */
/* Includes ------------------------------------------------------------------*/
#include "main.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */

/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */

/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/
I2C_HandleTypeDef hi2c1;

UART_HandleTypeDef huart1;
UART_HandleTypeDef huart2;
UART_HandleTypeDef huart3;

/* USER CODE BEGIN PV */

/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_I2C1_Init(void);
static void MX_USART1_UART_Init(void);
static void MX_USART2_UART_Init(void);
static void MX_USART3_UART_Init(void);
/* USER CODE BEGIN PFP */

/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */
typedef struct {
    float temperature;   // 温度
    float humidity;      // 湿度
    float pressure;      // 气压
    float latitude;      // 纬度
    float longitude;     // 经度
    float tds;           // TDS
    float water_temp;
} SensorData;
// ===== 2. 统一接口 =====
typedef struct {
    void (*init)(void);
    void (*read)(SensorData *data);
} Sensor;
// ===== 3. AHT20 封装 =====
#define AHT20_ADDR (0x38 << 1)
void AHT20_Init(void)
{
    uint8_t cmd[3] = {0xBE, 0x08, 0x00};
    HAL_I2C_Master_Transmit(&hi2c1, AHT20_ADDR, cmd, 3, 100);
    HAL_Delay(100);
}
void AHT20_Read(SensorData *data)
{
    uint8_t cmd[3] = {0xAC, 0x33, 0x00};
    uint8_t buf[6] = {0};
    HAL_I2C_Master_Transmit(&hi2c1, AHT20_ADDR, cmd, 3, 100);
    HAL_Delay(100);
    HAL_I2C_Master_Receive(&hi2c1, AHT20_ADDR, buf, 6, 100);
    uint32_t hum_raw = (buf[1] << 12) | (buf[2] << 4) | (buf[3] >> 4);
    uint32_t temp_raw = ((buf[3] & 0x0F) << 16) | (buf[4] << 8) | buf[5];
    data->humidity = hum_raw * 100.0f / 1048576.0f;
    data->temperature = temp_raw * 200.0f / 1048576.0f - 50.0f;
}
// ===== 4. BMP280 封装 =====
#define BMP280_ADDR (0x77 << 1)
uint16_t dig_T1; int16_t dig_T2, dig_T3;
uint16_t dig_P1; int16_t dig_P2, dig_P3, dig_P4, dig_P5, dig_P6, dig_P7, dig_P8, dig_P9;
void BMP280_Init(void)
{
    uint8_t data = 0x33;
    HAL_I2C_Mem_Write(&hi2c1, BMP280_ADDR, 0xF4, 1, &data, 1, 100);
    data = 0x08;
    HAL_I2C_Mem_Write(&hi2c1, BMP280_ADDR, 0xF5, 1, &data, 1, 100);
    uint8_t cal[24];
    HAL_I2C_Mem_Read(&hi2c1, BMP280_ADDR, 0x88, 1, cal, 24, 100);
    dig_T1 = (cal[1]<<8)|cal[0];
    dig_T2 = (int16_t)((cal[3]<<8)|cal[2]);
    dig_T3 = (int16_t)((cal[5]<<8)|cal[4]);
    dig_P1 = (cal[7]<<8)|cal[6];
    dig_P2 = (int16_t)((cal[9]<<8)|cal[8]);
    dig_P3 = (int16_t)((cal[11]<<8)|cal[10]);
    dig_P4 = (int16_t)((cal[13]<<8)|cal[12]);
    dig_P5 = (int16_t)((cal[15]<<8)|cal[14]);
    dig_P6 = (int16_t)((cal[17]<<8)|cal[16]);
    dig_P7 = (int16_t)((cal[19]<<8)|cal[18]);
    dig_P8 = (int16_t)((cal[21]<<8)|cal[20]);
    dig_P9 = (int16_t)((cal[23]<<8)|cal[22]);
}
void BMP280_Read(SensorData *data)
{
    uint8_t p_msb, p_lsb, p_xlsb, t_msb, t_lsb, t_xlsb;
    HAL_I2C_Mem_Read(&hi2c1, BMP280_ADDR, 0xF7, 1, &p_msb, 1, 100);
    HAL_I2C_Mem_Read(&hi2c1, BMP280_ADDR, 0xF8, 1, &p_lsb, 1, 100);
    HAL_I2C_Mem_Read(&hi2c1, BMP280_ADDR, 0xF9, 1, &p_xlsb, 1, 100);
    HAL_I2C_Mem_Read(&hi2c1, BMP280_ADDR, 0xFA, 1, &t_msb, 1, 100);
    HAL_I2C_Mem_Read(&hi2c1, BMP280_ADDR, 0xFB, 1, &t_lsb, 1, 100);
    HAL_I2C_Mem_Read(&hi2c1, BMP280_ADDR, 0xFC, 1, &t_xlsb, 1, 100);
    int32_t adc_P = ((p_msb << 16) | (p_lsb << 8) | p_xlsb) >> 4;
    int32_t adc_T = ((t_msb << 16) | (t_lsb << 8) | t_xlsb) >> 4;
    double var1 = ((double)adc_T/16384.0 - (double)dig_T1/1024.0) * (double)dig_T2;
    double var2 = (((double)adc_T/131072.0 - (double)dig_T1/8192.0) *
                   ((double)adc_T/131072.0 - (double)dig_T1/8192.0)) * (double)dig_T3;
    double t_fine = var1 + var2;
    var1 = t_fine/2.0 - 64000.0;
    var2 = var1 * var1 * (double)dig_P6 / 32768.0;
    var2 = var2 + var1 * (double)dig_P5 * 2.0;
    var2 = var2/4.0 + (double)dig_P4 * 65536.0;
    var1 = ((double)dig_P3 * var1 * var1 / 524288.0 + (double)dig_P2 * var1) / 524288.0;
    var1 = (1.0 + var1/32768.0) * (double)dig_P1;
    if (var1 == 0.0) { data->pressure = 0; return; }
    double p = 1048576.0 - (double)adc_P;
    p = (p - var2/4096.0) * 6250.0 / var1;
    var1 = (double)dig_P9 * p * p / 2147483648.0;
    var2 = p * (double)dig_P8 / 32768.0;
    p = p + (var1 + var2 + (double)dig_P7) / 16.0;
    data->pressure = p / 100.0;   // hPa
}
// ===== 5. GPS 封装（UART 异步，轮询接�? + 全局变量�?=====
uint8_t gps_rx_byte;
uint8_t tds_rx_byte;
volatile float gps_lat = 0, gps_lon = 0;
char gps_line[128];
int gps_line_idx = 0;
void gps_parse(char *line)
{
    if (strncmp(line, "$GNRMC", 6) != 0) return;
    char *token, *saveptr;
    int field = 0;
    char status = 0, ns = 0, ew = 0;
    char lat_str[16] = "", lon_str[16] = "";
    token = strtok_r(line, ",", &saveptr);
    while (token != NULL)
    {
        switch (field)
        {
            case 2: status = token[0]; break;
            case 3: strcpy(lat_str, token); break;
            case 4: ns = token[0]; break;
            case 5: strcpy(lon_str, token); break;
            case 6: ew = token[0]; break;
        }
        field++;
        token = strtok_r(NULL, ",", &saveptr);
    }
    if (status == 'A' && lat_str[0] && lon_str[0])
    {
        float lat = atof(lat_str), lon = atof(lon_str);
        int lat_deg = (int)(lat/100), lon_deg = (int)(lon/100);
        gps_lat = lat_deg + (lat - lat_deg*100)/60.0;
        gps_lon = lon_deg + (lon - lon_deg*100)/60.0;
        if (ns == 'S') gps_lat = -gps_lat;
        if (ew == 'W') gps_lon = -gps_lon;
    }
}
void GPS_Init(void)
{
    gps_line_idx = 0;
    HAL_UART_Receive_IT(&huart2, &gps_rx_byte, 1);   // 启动中断接收
}
void GPS_Poll(void)
{
    uint8_t ch;
    if (HAL_UART_Receive(&huart2, &ch, 1, 10) == HAL_OK)
    {
        if (ch == '\n') { gps_line[gps_line_idx]='\0'; gps_parse(gps_line); gps_line_idx=0; }
        else if (gps_line_idx < 127) gps_line[gps_line_idx++] = ch;
    }
}
void GPS_Read(SensorData *data)
{
    data->latitude = gps_lat;
    data->longitude = gps_lon;
}
// ===== 6. TDS 封装（UART 异步�?6字节帧）=====
volatile float tds_value = 0;
volatile float tds_temp_value = 0;
uint8_t tds_frame[6];
int tds_frame_idx = 0;
void tds_parse(uint8_t *buf)
{
    if (buf[0] != 0x55 || buf[5] != 0xEE) return;
    uint16_t temp_raw = (buf[1] << 8) | buf[2];   // 温度×10
    uint16_t tds_raw  = (buf[3] << 8) | buf[4];
    tds_temp_value = temp_raw / 10.0f;            // 水温
    tds_value = tds_raw;
}
void TDS_Init(void)
{
    tds_frame_idx = 0;
    HAL_UART_Receive_IT(&huart3, &tds_rx_byte, 1);
}
void TDS_Poll(void)
{
    uint8_t ch;
    if (HAL_UART_Receive(&huart3, &ch, 1, 10) == HAL_OK)
    {
        if (tds_frame_idx == 0) { if (ch == 0x55) tds_frame[tds_frame_idx++] = ch; }
        else
        {
            tds_frame[tds_frame_idx++] = ch;
            if (tds_frame_idx == 6) { tds_parse(tds_frame); tds_frame_idx = 0; }
        }
    }
}
void TDS_Read(SensorData *data) {
	data->tds = tds_value;
	data->water_temp = tds_temp_value;
}
// ===== 7. 传感器注�? =====
Sensor AHT20_Sensor  = { AHT20_Init,  AHT20_Read  };
Sensor BMP280_Sensor = { BMP280_Init, BMP280_Read };
Sensor GPS_Sensor    = { GPS_Init,    GPS_Read    };
Sensor TDS_Sensor    = { TDS_Init,    TDS_Read    };
Sensor *sensors[] = { &AHT20_Sensor, &BMP280_Sensor, &GPS_Sensor, &TDS_Sensor };
/* USER CODE END 0 */

/**
  * @brief  The application entry point.
  * @retval int
  */
int main(void)
{

  /* USER CODE BEGIN 1 */

  /* USER CODE END 1 */

  /* MCU Configuration--------------------------------------------------------*/

  /* Reset of all peripherals, Initializes the Flash interface and the Systick. */
  HAL_Init();

  /* USER CODE BEGIN Init */

  /* USER CODE END Init */

  /* Configure the system clock */
  SystemClock_Config();

  /* USER CODE BEGIN SysInit */

  /* USER CODE END SysInit */

  /* Initialize all configured peripherals */
  MX_GPIO_Init();
  MX_I2C1_Init();
  MX_USART1_UART_Init();
  MX_USART2_UART_Init();
  MX_USART3_UART_Init();
  /* USER CODE BEGIN 2 */
  for (int i = 0; i < 4; i++) sensors[i]->init();
  uint32_t last_tick = 0;
  /* USER CODE END 2 */

  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
  while (1)
  {
      //GPS_Poll();   // 轮询 GPS 串口
      //TDS_Poll();   // 轮询 TDS 串口
      if (HAL_GetTick() - last_tick >= 2000)
      {
          SensorData data = {0};
          for (int i = 0; i < 4; i++) sensors[i]->read(&data);
          char buf[128];
          int len = sprintf(buf, "#01,%.1f,%.1f,%.0f,%.4f,%.4f,%.0f,%.1f\r\n",
        	        data.temperature, data.humidity, data.pressure,
        	        data.latitude, data.longitude, data.tds, data.water_temp);
          HAL_UART_Transmit(&huart1, (uint8_t*)buf, len, 100);
          last_tick = HAL_GetTick();
      }
    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */
  }
  /* USER CODE END 3 */
}

/**
  * @brief System Clock Configuration
  * @retval None
  */
void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

  /** Initializes the RCC Oscillators according to the specified parameters
  * in the RCC_OscInitTypeDef structure.
  */
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE;
  RCC_OscInitStruct.HSEState = RCC_HSE_ON;
  RCC_OscInitStruct.HSEPredivValue = RCC_HSE_PREDIV_DIV1;
  RCC_OscInitStruct.HSIState = RCC_HSI_ON;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
  RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSE;
  RCC_OscInitStruct.PLL.PLLMUL = RCC_PLL_MUL9;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }

  /** Initializes the CPU, AHB and APB buses clocks
  */
  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
                              |RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV2;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_2) != HAL_OK)
  {
    Error_Handler();
  }
}

/**
  * @brief I2C1 Initialization Function
  * @param None
  * @retval None
  */
static void MX_I2C1_Init(void)
{

  /* USER CODE BEGIN I2C1_Init 0 */

  /* USER CODE END I2C1_Init 0 */

  /* USER CODE BEGIN I2C1_Init 1 */

  /* USER CODE END I2C1_Init 1 */
  hi2c1.Instance = I2C1;
  hi2c1.Init.ClockSpeed = 100000;
  hi2c1.Init.DutyCycle = I2C_DUTYCYCLE_2;
  hi2c1.Init.OwnAddress1 = 0;
  hi2c1.Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
  hi2c1.Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
  hi2c1.Init.OwnAddress2 = 0;
  hi2c1.Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
  hi2c1.Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;
  if (HAL_I2C_Init(&hi2c1) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN I2C1_Init 2 */

  /* USER CODE END I2C1_Init 2 */

}

/**
  * @brief USART1 Initialization Function
  * @param None
  * @retval None
  */
static void MX_USART1_UART_Init(void)
{

  /* USER CODE BEGIN USART1_Init 0 */

  /* USER CODE END USART1_Init 0 */

  /* USER CODE BEGIN USART1_Init 1 */

  /* USER CODE END USART1_Init 1 */
  huart1.Instance = USART1;
  huart1.Init.BaudRate = 9600;
  huart1.Init.WordLength = UART_WORDLENGTH_8B;
  huart1.Init.StopBits = UART_STOPBITS_1;
  huart1.Init.Parity = UART_PARITY_NONE;
  huart1.Init.Mode = UART_MODE_TX_RX;
  huart1.Init.HwFlowCtl = UART_HWCONTROL_NONE;
  huart1.Init.OverSampling = UART_OVERSAMPLING_16;
  if (HAL_UART_Init(&huart1) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN USART1_Init 2 */

  /* USER CODE END USART1_Init 2 */

}

/**
  * @brief USART2 Initialization Function
  * @param None
  * @retval None
  */
static void MX_USART2_UART_Init(void)
{

  /* USER CODE BEGIN USART2_Init 0 */

  /* USER CODE END USART2_Init 0 */

  /* USER CODE BEGIN USART2_Init 1 */

  /* USER CODE END USART2_Init 1 */
  huart2.Instance = USART2;
  huart2.Init.BaudRate = 9600;
  huart2.Init.WordLength = UART_WORDLENGTH_8B;
  huart2.Init.StopBits = UART_STOPBITS_1;
  huart2.Init.Parity = UART_PARITY_NONE;
  huart2.Init.Mode = UART_MODE_TX_RX;
  huart2.Init.HwFlowCtl = UART_HWCONTROL_NONE;
  huart2.Init.OverSampling = UART_OVERSAMPLING_16;
  if (HAL_UART_Init(&huart2) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN USART2_Init 2 */

  /* USER CODE END USART2_Init 2 */

}

/**
  * @brief USART3 Initialization Function
  * @param None
  * @retval None
  */
static void MX_USART3_UART_Init(void)
{

  /* USER CODE BEGIN USART3_Init 0 */

  /* USER CODE END USART3_Init 0 */

  /* USER CODE BEGIN USART3_Init 1 */

  /* USER CODE END USART3_Init 1 */
  huart3.Instance = USART3;
  huart3.Init.BaudRate = 9600;
  huart3.Init.WordLength = UART_WORDLENGTH_8B;
  huart3.Init.StopBits = UART_STOPBITS_1;
  huart3.Init.Parity = UART_PARITY_NONE;
  huart3.Init.Mode = UART_MODE_TX_RX;
  huart3.Init.HwFlowCtl = UART_HWCONTROL_NONE;
  huart3.Init.OverSampling = UART_OVERSAMPLING_16;
  if (HAL_UART_Init(&huart3) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN USART3_Init 2 */

  /* USER CODE END USART3_Init 2 */

}

/**
  * @brief GPIO Initialization Function
  * @param None
  * @retval None
  */
static void MX_GPIO_Init(void)
{
/* USER CODE BEGIN MX_GPIO_Init_1 */
/* USER CODE END MX_GPIO_Init_1 */

  /* GPIO Ports Clock Enable */
  __HAL_RCC_GPIOD_CLK_ENABLE();
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOB_CLK_ENABLE();

/* USER CODE BEGIN MX_GPIO_Init_2 */
/* USER CODE END MX_GPIO_Init_2 */
}

/* USER CODE BEGIN 4 */
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart == &huart2)   // GPS
    {
        if (gps_rx_byte == '\n')
        {
            gps_line[gps_line_idx] = '\0';
            gps_parse(gps_line);
            gps_line_idx = 0;
        }
        else if (gps_line_idx < 127)
        {
            gps_line[gps_line_idx++] = gps_rx_byte;
        }
        HAL_UART_Receive_IT(&huart2, &gps_rx_byte, 1);   // 重新启动
    }
    else if (huart == &huart3)   // TDS
    {
        if (tds_frame_idx == 0)
        {
            if (tds_rx_byte == 0x55) tds_frame[tds_frame_idx++] = tds_rx_byte;
        }
        else
        {
            tds_frame[tds_frame_idx++] = tds_rx_byte;
            if (tds_frame_idx == 6) { tds_parse(tds_frame); tds_frame_idx = 0; }
        }
        HAL_UART_Receive_IT(&huart3, &tds_rx_byte, 1);
    }
}
/* USER CODE END 4 */

/**
  * @brief  This function is executed in case of error occurrence.
  * @retval None
  */
void Error_Handler(void)
{
  /* USER CODE BEGIN Error_Handler_Debug */
  /* User can add his own implementation to report the HAL error return state */
  __disable_irq();
  while (1)
  {
  }
  /* USER CODE END Error_Handler_Debug */
}

#ifdef  USE_FULL_ASSERT
/**
  * @brief  Reports the name of the source file and the source line number
  *         where the assert_param error has occurred.
  * @param  file: pointer to the source file name
  * @param  line: assert_param error line source number
  * @retval None
  */
void assert_failed(uint8_t *file, uint32_t line)
{
  /* USER CODE BEGIN 6 */
  /* User can add his own implementation to report the file name and line number,
     ex: printf("Wrong parameters value: file %s on line %d\r\n", file, line) */
  /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */
